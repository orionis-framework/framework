"""Adapt pydoctor's source model to the Python syntax used by Orionis."""

from __future__ import annotations
import ast
from collections import defaultdict
from functools import cache
from typing import TYPE_CHECKING
from urllib.parse import quote
from docutils import nodes # pyright: ignore[reportMissingModuleSource]
from pydoctor import astbuilder, astutils, epydoc2stan, model

if TYPE_CHECKING:
    from pydoctor.epydoc.markup import ParsedDocstring # pyright: ignore[reportMissingImports]
    from pydoctor.options import Options # pyright: ignore[reportMissingImports]

class _PortableUrls:
    """Resolve documentation links without case-sensitive filename collisions."""

    @property
    def url(self) -> str:
        """Return the unique page URL and optional member anchor.

        Returns
        -------
        str
            Portable relative URL for the documented object.
        """
        page = self.page_object
        page_url = self.system.pageUrls.get(page.fullName())
        if page_url is None:
            return super().url
        if page is self:
            return page_url
        return f"{page_url}#{quote(self.name)}"

def _stabilize_toc(parsed: ParsedDocstring, depth: int) -> None:
    """Keep repeated sidebar rendering from creating dangling section backlinks.

    Parameters
    ----------
    parsed : pydoctor.epydoc.markup.ParsedDocstring
        Parsed documentation whose headings are shared by multiple sidebars.
    depth : int
        Configured depth of the sidebar table of contents.

    Returns
    -------
    None
        Cache forward navigation while leaving section titles unlinked.
    """
    original = parsed.get_toc

    @cache
    def get_toc(depth: int) -> ParsedDocstring | None:
        """Build one stable table of contents for each requested depth.

        Parameters
        ----------
        depth : int
            Maximum number of heading levels to include.

        Returns
        -------
        pydoctor.epydoc.markup.ParsedDocstring or None
            Forward links to section headings, without duplicate entry IDs.
        """
        toc = original(depth)
        if toc is not None:
            for title in parsed.to_node().findall(nodes.title):
                title.attributes.pop("refid", None)
            for reference in toc.to_node().findall(nodes.reference):
                reference["ids"] = []
        return toc

    parsed.get_toc = get_toc
    get_toc(depth)

def _copy_syntax[T](value: T) -> T:
    """Copy syntax fields without copying pydoctor's parent-reference graphs.

    Parameters
    ----------
    value : object
        Syntax node, field list or scalar belonging to the parsed source tree.

    Returns
    -------
    object
        Independent syntax data with source locations preserved.
    """
    if isinstance(value, ast.AST):
        copied = type(value)(**{
            name: _copy_syntax(field) for name, field in ast.iter_fields(value)
        })
        return ast.copy_location(copied, value)
    if isinstance(value, list):
        return [_copy_syntax(item) for item in value]
    return value

class _TypeAliasNormalizer(ast.NodeTransformer):
    """Expose PEP 695 aliases to pydoctor's existing type-alias processor."""

    def visitTypeAlias(self, node: ast.TypeAlias) -> ast.AnnAssign:
        """Translate an alias only in the documentation syntax tree.

        Parameters
        ----------
        node : ast.TypeAlias
            Source alias with its original value and location.

        Returns
        -------
        ast.AnnAssign
            Equivalent declaration recognized by pydoctor 25.10.
        """
        return ast.copy_location(
            ast.AnnAssign(
                target=node.name,
                annotation=ast.Attribute(
                    value=ast.Name(id="typing", ctx=ast.Load()),
                    attr="TypeAlias",
                    ctx=ast.Load(),
                ),
                value=node.value,
                simple=1,
            ),
            node,
        )

    visit_TypeAlias = visitTypeAlias  # noqa: N815 - ast.NodeVisitor protocol

class _AnnotationParser(astutils._AnnotationStringParser):  # noqa: SLF001
    """Preserve literal validation metadata while resolving forward references."""

    def visitSubscript(self, node: ast.Subscript) -> ast.Subscript:
        """Parse only type positions in Annotated and Literal declarations.

        Parameters
        ----------
        node : ast.Subscript
            Type expression, including the framework's Field and Choice aliases.

        Returns
        -------
        ast.Subscript
            Annotation with metadata strings and validation messages preserved.
        """
        name = ast.unparse(node.value).rsplit(".", 1)[-1]
        if name in {"Literal", "Choice"}:
            return node
        if name in {"Annotated", "Field"} and isinstance(node.slice, ast.Tuple):
            annotation = _copy_syntax(node)
            annotation.slice.elts[0] = self.visit(annotation.slice.elts[0])
            return annotation
        return super().visit_Subscript(node)

    visit_Subscript = visitSubscript  # noqa: N815 - ast.NodeVisitor protocol

class _ModuleVisitor(astbuilder.ModuleVistor):
    """Build attribute documentation without interpreting metadata as type names."""

    def visitAnnAssign(self, node: ast.AnnAssign) -> None:
        """Process an annotated assignment with metadata-aware string parsing.

        Parameters
        ----------
        node : ast.AnnAssign
            Attribute or type-alias declaration being documented.

        Returns
        -------
        None
            Record the attribute, its documentation and any genuine parse errors.
        """
        current = self.builder.current
        try:
            annotation = _AnnotationParser().visit(_copy_syntax(node.annotation))
        except SyntaxError as error:
            current.module.report(
                f"syntax error in annotation: {error}",
                lineno_offset=node.annotation.lineno,
                section="annotation",
            )
            annotation = node.annotation
        annotation = astutils.upgrade_annotation(annotation, current)
        try:
            if isinstance(node.target, ast.Name) and astutils.is_using_annotations(
                annotation,
                ("typing.TypeAlias", "typing_extensions.TypeAlias"),
                current,
            ):
                # Explicit aliases must remain documented objects even when their
                # value is a single imported name, such as HttpResponse = Response.
                if isinstance(current, model.Module):
                    self._handleModuleVar(
                        node.target.id, annotation, node.value, node.lineno,
                        augassign=None,
                    )
                elif isinstance(current, model.Class):
                    self._handleClassVar(
                        node.target.id, annotation, node.value, node.lineno,
                        augassign=None,
                    )
            else:
                self._handleAssignment(node.target, annotation, node.value, node.lineno)
        except astbuilder.IgnoreAssignment:
            return
        self._handleAssignmentDoc(node, node.target)

    visit_AnnAssign = visitAnnAssign  # noqa: N815 - ast.NodeVisitor protocol

class _ASTBuilder(astbuilder.ASTBuilder):
    """Normalize documentation trees without modifying framework runtime code."""

    ModuleVistor = _ModuleVisitor

    def processModuleAST(self, mod_ast: ast.Module, mod: model.Module) -> None:
        """Build documentation from a normalized copy of the source tree.

        Parameters
        ----------
        mod_ast : ast.Module
            Parsed source module.
        mod : pydoctor.model.Module
            Documentation object receiving the parsed definitions.

        Returns
        -------
        None
            Populate the model with functions, classes and modern type aliases.
        """
        normalized = _TypeAliasNormalizer().visit(_copy_syntax(mod_ast))
        ast.fix_missing_locations(normalized)
        astutils.Parentage().visit(normalized)
        super().processModuleAST(normalized, mod)

class DocumentationSystem(model.System):
    """Document Orionis with support for its type aliases and schema metadata."""

    defaultBuilder = _ASTBuilder  # noqa: N815 - pydoctor System protocol

    def __init__(self, options: Options | None = None) -> None:
        """Initialize a model with portable URLs for every documentable kind.

        Parameters
        ----------
        options : pydoctor.options.Options or None, optional
            Generator options, or None to use pydoctor defaults.

        Returns
        -------
        None
            Register URL handling before the source model is populated.
        """
        super().__init__(options)
        self.pageUrls: dict[str, str] = {}
        for kind in ("Class", "Function", "Module", "Package", "Attribute"):
            self._factory.add_mixin(kind, _PortableUrls)

    def _assignPageUrls(self) -> None:
        """Disambiguate page names that would overwrite each other on Windows.

        Returns
        -------
        None
            Retain public class URLs and suffix conflicting module filenames.
        """
        groups = defaultdict(list)
        for obj in self.allobjects.values():
            if obj.documentation_location is model.DocLocation.OWN_PAGE:
                groups[obj.url.casefold()].append(obj)
        used = set(groups)
        for group in groups.values():
            ordered = sorted(group, key=lambda obj: (
                isinstance(obj, model.Module), obj.fullName(),
            ))
            for obj in ordered[1:]:
                stem = obj.url.removesuffix(".html")
                kind = obj.kind.name.lower()
                candidate = f"{stem}.{kind}.html"
                counter = 2
                while candidate.casefold() in used:
                    candidate = f"{stem}.{kind}-{counter}.html"
                    counter += 1
                used.add(candidate.casefold())
                self.pageUrls[obj.fullName()] = candidate

    def postProcess(self) -> None: # NOSONAR
        """Recognize NumPy attribute descriptions in documentation coverage.

        Returns
        -------
        None
            Retain parsed field markup while making its text available to
            pydoctor's undocumented-object index.
        """
        super().postProcess()
        self._assignPageUrls()
        for obj in self.allobjects.values():
            epydoc2stan.ensure_parsed_docstring(obj)
            if obj.docstring is None and obj.parsed_docstring is not None:
                obj.docstring = obj.parsed_docstring.to_text()
            if obj.isVisible and not any(
                source.docstring and source.docstring.strip()
                for source in obj.docsources()
            ):
                obj.report("Missing API documentation.", section="documentation")
            if obj.parsed_docstring is not None:
                _stabilize_toc(obj.parsed_docstring, self.options.sidebartocdepth)
                if isinstance(obj, model.Function) and "return" in obj.annotations:
                    descriptions = (
                        field.body().to_text().strip()
                        for field in obj.parsed_docstring.fields
                        if field.tag() in {"return", "returns", "yield", "yields"}
                    )
                    if not any(descriptions):
                        obj.report(
                            "Missing return or yield description.",
                            section="documentation",
                        )
                    tags = {field.tag() for field in obj.parsed_docstring.fields}
                    if tags & {"yield", "yields"} and not tags & {
                        "return", "returns", "rtype", "returntype",
                    }:
                        # NumPy generators document their output with Yields.
                        # Keep the iterator annotation in obj.signature while
                        # avoiding an additional, empty inferred Returns table.
                        obj.annotations = {
                            name: annotation
                            for name, annotation in obj.annotations.items()
                            if name != "return"
                        }
