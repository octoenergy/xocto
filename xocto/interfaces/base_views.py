"""
Base classes for views that use template serializers to avoid passing rich objects into the
template context.
"""
import enum
import re
from collections.abc import Sequence
from typing import Any, Optional

from django import forms, http, shortcuts
from django.conf import settings
from django.contrib import messages
from django.http import response
from django.views import generic
from rest_framework import serializers

from xocto import storage


class SerializedListView(generic.ListView):
    """
    Base class for a list view that uses a serializer to convert the queryset into primitive Python
    data structures for the template.

    Subclasses need to either:

    1. Define the serializer_class class var
    2. Override get_serializer_class to return a serializer class

    More fine-grained customisation can be achieved by overriding the other serializer construction
    methods (which are modelled off Django's django.views.generic.edit.FormMixin).

    Tips for creating a template serializer class:

    - Use `DateTimeField(format=None)` for datetime fields to pass the datetime instance to the
      template (rather than the default of serializing it to a string).

    - Use the `source` attribute to Fields to indicate which property/method from the model
      instance to use. This works for related models, eg:

          team_pk = serializers.CharField(source="team.pk", allow_null=True)

      Remember to use `allow_null=True` if the FK is nullable.

    - Use SerializerMethod fields to call a method on the serializer class to compute a field.

    - Prefer to use `pk` rather than `id` as a field-name (to avoid shadowing a Python builtin)

    - To compute queryset-level variables (eg a sum of a field across all instances), override the
      class-level many_init function like so:

          @classmethod
          def many_init(cls, *args, **kwargs):
              # Compute queryset-level var and pass to super() so it gets injected into each
              # object-level serializer instance.
              some_var = cls.some_function()
              return super().many_init(some_var=some_var, *args, **kwargs)

          @classmethod
          def some_function(cls):
              ...

          def __init__(self, some_var, *args, **kwargs):
              self.some_var = some_var
              super().__init__(*args, **kwargs)
    """

    # This should be a subclass of rest_framework.serializers.Serializer
    serializer_class: serializers.Serializer = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Remove the object_list key from the context so the queryset isn't available
        # in the template at all.
        queryset = context.pop("object_list")

        # Assign the serialized queryset
        context_object_name = self.get_context_object_name(queryset) or "object_list"
        context[context_object_name] = self.get_serialized_queryset(queryset)

        return context

    def get_serialized_queryset(self, queryset):
        serializer = self.get_serializer(queryset)
        return serializer.data

    def get_serializer(self, queryset, serializer_class=None):
        if serializer_class is None:
            serializer_class = self.get_serializer_class()
        return serializer_class(**self.get_serializer_kwargs(queryset))

    def get_serializer_class(self):
        return self.serializer_class

    def get_serializer_kwargs(self, queryset):
        return {"instance": queryset, "many": True, "context": self.get_serializer_context()}

    def get_serializer_context(self) -> dict:
        return {"request": self.request}


class SerializedDetailView(generic.DetailView):
    """
    Base class for a detail view that uses a serializer to convert the object into primitive Python
    data structures for the template.
    """

    # This should be a subclass of rest_framework.serializers.Serializer
    serializer_class: serializers.Serializer = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Remove the object key from the context so the object isn't available in the template at all.
        object_ = context.pop("object")

        # Assign the serialized object
        context_object_name = self.get_context_object_name(object_) or "object"
        context[context_object_name] = self.get_serialized_object(object_)

        return context

    def get_serialized_object(self, object_):
        serializer = self.get_serializer(object_)
        return serializer.data

    def get_serializer(self, object_, serializer_class=None):
        if serializer_class is None:
            serializer_class = self.get_serializer_class()
        return serializer_class(**self.get_serializer_kwargs(object_))

    def get_serializer_class(self):
        return self.serializer_class

    def get_serializer_kwargs(self, object_):
        return {"instance": object_}


class S3FilesExplorer(generic.TemplateView):
    class Action(enum.Enum):
        ARCHIVE = "archive"
        MOVE = "move"

    class Search(forms.Form):
        q = forms.CharField(
            label="Filename",
            required=False,
            widget=forms.TextInput(
                attrs={
                    "class": "form-control",
                    "data-placement": "right",
                    "placeholder": "Prefix or complete filename",
                }
            ),
        )

    template_name = "support/file-explorer.html"
    form_class = Search

    nest_by_date_on_move: bool = False
    nest_by_date_on_archive: bool = True
    missing_source_file_message: str = "{source_path} does not exist."
    destination_file_exists_message: str = "{destination_path} already exists."
    source_file_is_immovable_message: str = "{source_path} could not be moved."
    source_file_moved_message: str = "{source_path} moved to {destination_path}."

    s3_source_bucket: str = settings.S3_FILESERVER_BUCKET
    source_root: str
    s3_archive_bucket: str = settings.S3_ARCHIVE_BUCKET
    archive_root: Optional[str] = None

    file_explorer_slug: str
    file_mover_slug: Optional[str] = None
    file_archiver_slug: Optional[str] = None
    related_explorers: Sequence[tuple[str, str]] = ()
    domain: Optional[str] = None
    immovable_filename_pattern: Optional[re.Pattern] = None

    action: Optional[Action] = None

    class _MoveNotSupported(Exception):
        pass

    def dispatch(self, request, path="", *args, **kwargs) -> response.HttpResponseBase:
        """
        Display contents of s3://<View.s3_source_bucket>/<View.source_root>/<path>.

        This is the behaviour if no `View.action` is specified.

        If the URI described above points at a leaf key with an associated file, this view
        redirects to a self-signed URL for the file.

        If the URI does not point at such a leaf key, then child nodes (when treating the keys as a
        hierarchical file system) are listed, each linking back to this view with the path now
        pointing to them.  In this list view, all of the ancestor nodes that make up the current
        path (i.e. not including the `View.s3_source_bucket` or `View.source_root`) are shown, also
        with links back to this view with the path now pointing to them.  Together, this allows for
        full navigation up and down the "file system" within the given `View.source_root`.

        Listed leaf keys are also determined to be "movable" if their "file" name doesn't match an
        optional regex pattern (`immovabled_filename_pattern`) describing the names of "files" that
        should not be moved, and either:
        * there is a view slug configured (`file_mover_slug`) for handling "move" requests.
        * there is a view slug and archive-location root configured (`file_archiver_slug` and
          `archive_root`, respectively) for handling "archive" requests.

        If `View.action` is specified, the contents display behaviour is not carried out, and the
        specified action is carried out within the same context instead.  More detail on the
        behaviour of the actions can be found in their own methods.
        """
        if self.action:
            return {self.Action.MOVE: self.move_file, self.Action.ARCHIVE: self.archive_file}[
                self.action
            ](request, *args, **kwargs)

        self.breadcrumbs = self._get_sanitised_breadcrumbs(path)

        store = storage.store(self.s3_source_bucket)
        # Ensure that the namespace is /-terminated, to avoid partial matches, e.g.
        # >>> print(key.key for key in store.list_s3_keys(namespace="foo/bar"))
        # foo/baracuda
        s3_namespace = "/".join([self.source_root.rstrip("/"), *self.breadcrumbs, ""])
        self.prefix_length = len(s3_namespace)

        # Search by filename
        filename = self.request.GET.get("q", "")
        namespace = f"{s3_namespace}{filename}"

        self.keys, self.next_token = store.list_s3_keys_page(
            namespace=namespace,
            next_token=self.request.GET.get("next_token", ""),
        )
        # Try to get a presigned url for the namespace less the trailing / (treating it like a
        # complete key), if there are no keys in the namespace where it is treated as a directory.
        if not self.keys and store.exists(key_path := s3_namespace[:-1], as_file=True):  # type: ignore[truthy-bool]
            return shortcuts.redirect(store.fetch_url(key_path))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs) -> http.HttpResponse:
        self.form = self.form_class(request.GET or None)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs) -> dict:
        """
        Loads the various configuration values and the sub-key details into the context.
        """
        context = super().get_context_data(**kwargs)
        context["form"] = self.form

        directories = set()
        files: list[dict[str, Any]] = []

        # Each key here is (in production) a boto key:
        # http://boto.cloudhackers.com/en/latest/ref/s3.html#module-boto.s3.key
        # Crucially they have the following attributes:
        # * key: the absolute "path" of the key within its bucket.
        # * generate_url: a method to generate a temporary self-signed url to access the contents
        #   of the key directly from its bucket.
        store = storage.store(self.s3_source_bucket)
        for key in self.keys:
            node_name, *descendants = key.key[self.prefix_length :].split("/")
            if descendants:
                directories.add(node_name)
            else:
                details = {
                    "name": node_name,
                    "download_link": store.fetch_url(key_path=key.key, expires_in=60),
                }
                if not self._file_is_movable(node_name):
                    details["not_moveable"] = True  # type: ignore[assignment]
                files.append(details)

        context["directories"] = sorted(directories)
        context["files"] = sorted(files, key=lambda details: details["name"])

        context["breadcrumbs"] = self.breadcrumbs
        context["path"] = "/".join([*self.breadcrumbs, ""])
        context["domain"] = self.domain
        context["file_explorer_slug"] = self.file_explorer_slug
        context["file_archiver_slug"] = self.file_archiver_slug
        context["file_mover_slug"] = self.file_mover_slug
        context["related_explorers"] = self.related_explorers

        if self.next_token:
            params = self.request.GET.copy()
            params["next_token"] = self.next_token
            context["next_page_url"] = self.request.path + "?" + params.urlencode()

        return context

    # Action methods

    def move_file(self, request, *args, **kwargs):
        """
        Moves the file specified in the `source` to the `destination` under the same root.

        This defaults the `destination` to the `View.source_root`, and defaults the destination
        filename to the filename of the source, if the `destination` is "/" terminated.  Moving
        will fail if the specified/implied destination path already exists.

        If configured to `View.nest_by_date_on_move`, will use the date on which the move was
        requested to further nest the file at the destination, i.e. at:
        s3://<View.s3_source_bucket>/<View.source_root>/<desitnation less the filename>/<year of
        move>/<month of move>/<day of move>/<filename of destination>

        For example, moving a file to destination "subdir/file.txt" on 2020/01/05 when configured
        with the source bucket "bucket", source root "test/directory" and `nest_by_date_on_move`
        set to `True` will result in moving the specified source key to the following key path:
        s3://bucket/test/directory/subdir/2020/01/05/file.txt
        """
        return self._move_file(
            request,
            self.s3_source_bucket,
            self.source_root,
            self.nest_by_date_on_move,
            *args,
            **kwargs,
        )

    def archive_file(self, request, *args, **kwargs):
        """
        Moves the file specified in the `source` to the `destination` in the configured archive.

        This defaults the `destination` to the `View.archive_root`, and defaults the destination
        filename to the filename of the source, if the `destination` is "/" terminated.  Archiving
        will fail if the specified/implied destination path already exists.

        If configured to `View.nest_by_date_on_archive`, will use the date on which the archival
        was requested to further nest the file at the destination, i.e. at:
        s3://<View.s3_archive_bucket>/<View.archive_root>/<desitnation less the filename>/<year of
        archival>/<month of archival>/<day of archival>/<filename of destination>

        For example, archiving a file to destination "subdir/file.txt" on 2020/01/05 when
        configured with the archive bucket "archive", source root "test/directory" and
        `nest_by_date_on_archive` set to `True` will result in moving the specified source key to
        the following key path:
        s3://archive/test/directory/subdir/2020/01/05/file.txt
        """
        return self._move_file(
            request,
            self.s3_archive_bucket,
            self.archive_root,
            self.nest_by_date_on_archive,
            *args,
            **kwargs,
        )

    # Private methods

    def _move_file(
        self, request, s3_destination_bucket, destination_root, nest_by_date, *args, **kwargs
    ) -> http.HttpResponse:
        source_path = request.GET["source"]
        destination_path = request.GET.get("destination", "/")
        destination_root = destination_root.rstrip("/")

        try:
            s3_source_key, filename = self._get_source_key_and_filename(source_path)
            destination, s3_namespace, filename = self._get_destination_descriptor(
                s3_destination_bucket,
                destination_root,
                destination_path,
                nest_by_date,
                default_filename=filename,
            )
        except self._MoveNotSupported as e:
            messages.error(request, str(e))  # noqa: G200
        else:
            store = storage.store(self.s3_source_bucket)
            contents = store.fetch_file_contents(s3_source_key.key)
            _, key_path = destination.store_file(
                namespace=s3_namespace, filename=filename, contents=contents
            )
            store.delete(s3_object=s3_source_key)

            prefix_length = len(destination_root) + 1
            messages.info(
                request,
                self.source_file_moved_message.format(
                    source_path=source_path, destination_path=key_path[prefix_length:]
                ),
            )

        return shortcuts.redirect(self._get_return_url(request, *args, **kwargs))

    def _get_return_url(self, request, *args, **kwargs) -> str:
        # Return either to the original page, if called via a clicked link, or to the Kraken home
        # page if accessed directly.
        return request.headers.get("referer", request.build_absolute_uri("/"))

    def _get_source_key_and_filename(self, source_path):
        sanitised_breadcrumbs = self._get_sanitised_breadcrumbs(source_path)
        sanitised_source_root = self.source_root.rstrip("/")

        if not self._file_is_movable(sanitised_breadcrumbs[-1]):
            raise self._MoveNotSupported(
                self.source_file_is_immovable_message.format(
                    source_path="/".join(sanitised_breadcrumbs)
                )
            )

        source = storage.store(self.s3_source_bucket)
        s3_key = source.get_key("/".join([sanitised_source_root, *sanitised_breadcrumbs]))
        if not s3_key:
            raise self._MoveNotSupported(
                self.missing_source_file_message.format(
                    source_path="/".join(sanitised_breadcrumbs)
                )
            )

        return s3_key, sanitised_breadcrumbs[-1]

    def _get_destination_descriptor(
        self,
        s3_destination_bucket,
        destination_root,
        destination_path,
        nest_by_date,
        default_filename,
    ):
        sanitised_breadcrumbs = self._get_sanitised_breadcrumbs(destination_path)
        if not destination_path or destination_path[-1] == "/":
            filename = default_filename
        else:
            filename = sanitised_breadcrumbs.pop()
        s3_namespace = "/".join([destination_root, *sanitised_breadcrumbs])

        destination = storage.store(s3_destination_bucket, use_date_in_key_path=nest_by_date)
        s3_key = destination.get_key("/".join([s3_namespace, filename]))
        if s3_key:
            raise self._MoveNotSupported(
                self.destination_file_exists_message.format(
                    destination_path="/".join([*sanitised_breadcrumbs, filename])
                )
            )

        return destination, s3_namespace, filename

    def _file_is_movable(self, filename: str) -> bool:
        if not (self.file_mover_slug or (self.file_archiver_slug and self.archive_root)):
            return False
        if self.immovable_filename_pattern:
            return not self.immovable_filename_pattern.match(filename)
        return True

    def _get_sanitised_breadcrumbs(self, path: str) -> list[str]:
        """
        Divides a path into its component breadcrumbs, resolving relative references.

        Resolves relative references, preventing movement up the hierarchy further than the `root`
        imposed by this view.  However, reverse navigation (`../`) up to the `root` is supported,
        so the paths given below will be sanitised as follows:
        * "/dir/file" -> ["dir", "file"]
        * "dir/file" -> ["dir", "file"]
        * "dir/../file" -> ["file"]
        * "../dir/file" -> ["dir", "file"]
        * "dir/subdir1/subdir2/../../subdir3/file" -> ["dir", "subdir3", "file"]
        * "dir//subdir1/./subdir2/../subdir3/../../file" -> ["dir", "file"]
        * "dir/subdir1/subdir2/../../../../file" -> ["file"]

        Such relative referencing is not introduced by the explorer itself, but may naturally used
        by users manually entering URLs.  This method ensures the explorer behaves as expected in
        such usecases.
        """
        path_parts = filter(lambda b: b and b not in (".", ""), path.split("/"))
        breadcrumbs: list[str] = []
        for part in path_parts:
            if part == "..":
                if breadcrumbs:
                    breadcrumbs.pop(-1)
            else:
                breadcrumbs.append(part)
        return breadcrumbs


class SoftWarningFormView(generic.FormView):
    """
    Base class for a form view that allows "soft" form validation warnings that are displayed to
    the user above the form after first submission, but can be ignored by submitting the form a
    second time.

    Achieves this by injecting a hidden form field that tracks the warnings that have been
    displayed to the user.

    Subclasses need to:
      - Override `check_for_warnings` to return a list of soft warning strings.
      - Ensure that their template renders these warnings properly (provided as `form_warnings` in
        template context). Most views will get this for free via the form partial template.
    """

    warnings: set[str] = set()

    def get_form(self, form_class: type[forms.BaseForm] | None = None) -> forms.BaseForm:
        form = super().get_form(form_class=form_class)

        # Inject a hidden field for tracking soft warnings the user has seen
        form.fields["displayed_warnings"] = forms.CharField(
            required=False, widget=forms.HiddenInput()
        )
        return form

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        # Copy request.POST so that form data is mutable
        if self.request.method in ("POST", "PUT"):
            kwargs["data"] = self.request.POST.copy()

        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            self.warnings = self.check_for_warnings(form)

            displayed_warnings = self._decode_displayed_warnings(
                form.cleaned_data.get("displayed_warnings", "")
            )

            # If there are warnings that haven't been displayed to the user yet, mark them as
            # displayed and re-render the form with them present
            if not self.warnings.issubset(displayed_warnings):
                form.data["displayed_warnings"] = self._encode_displayed_warnings(self.warnings)
                return self.render_to_response(self.get_context_data(form=form))

            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_warnings"] = sorted(self.warnings)
        return context

    def check_for_warnings(self, form) -> set[str]:
        """
        Build a set of soft warnings based on form data, to be displayed at the top of the form.
        """
        return set()

    def _encode_displayed_warnings(self, warnings: set[str]) -> str:
        return "|".join(warnings)

    def _decode_displayed_warnings(self, warnings: str) -> set[str]:
        return set(warnings.split("|")) if warnings else set()
