"""Fail-closed, provider-neutral engineering-tool adapters for VX Agents Fabric."""
from __future__ import annotations

import ast
import base64
import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Mapping

JSONMap = dict[str, Any]
OpenUrl = Callable[..., Any]


class ToolNotConfigured(RuntimeError):
    """The adapter contract exists but no provider endpoint is configured."""


class ToolInputError(ValueError):
    """A request or provider response violates the declared contract."""


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    version: str
    description: str
    allowed_scopes: tuple[str, ...]
    allowed_families: tuple[str, ...] = ("research", "engineering", "governance")
    required_capabilities: tuple[str, ...] = ()
    requires_explicit_approval: bool = False
    max_input_bytes: int = 1_000_000


@dataclass(frozen=True)
class ToolEvidence:
    tool_id: str
    tool_version: str
    input_sha256: str
    output_sha256: str
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolResult:
    status: str
    tool_id: str
    result: Mapping[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    evidence: ToolEvidence | None = None

    def to_dict(self) -> JSONMap:
        return asdict(self)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _read_json_response(response: Any, *, max_bytes: int = 2_000_000) -> JSONMap:
    raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ToolInputError("provider_response_too_large")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ToolInputError("provider_response_invalid_json") from exc
    if not isinstance(payload, dict):
        raise ToolInputError("provider_response_must_be_object")
    return payload


def _safe_endpoint(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password:
        return True
    return (parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
            and not parsed.username and not parsed.password)


# Each unit maps to dimension vector (length, mass, time) and scale-to-SI.
_UNITS: dict[str, tuple[tuple[int, int, int], float]] = {
    "m": ((1, 0, 0), 1.0), "km": ((1, 0, 0), 1000.0),
    "cm": ((1, 0, 0), 0.01), "mm": ((1, 0, 0), 0.001),
    "um": ((1, 0, 0), 1e-6), "in": ((1, 0, 0), 0.0254),
    "ft": ((1, 0, 0), 0.3048), "kg": ((0, 1, 0), 1.0),
    "g": ((0, 1, 0), 0.001), "mg": ((0, 1, 0), 1e-6),
    "s": ((0, 0, 1), 1.0), "ms": ((0, 0, 1), 0.001),
    "min": ((0, 0, 1), 60.0), "h": ((0, 0, 1), 3600.0),
    "m/s": ((1, 0, -1), 1.0), "km/h": ((1, 0, -1), 1000.0 / 3600.0),
    "N": ((1, 1, -2), 1.0), "kN": ((1, 1, -2), 1000.0),
    "Pa": ((-1, 1, -2), 1.0), "kPa": ((-1, 1, -2), 1000.0),
    "MPa": ((-1, 1, -2), 1_000_000.0), "GPa": ((-1, 1, -2), 1_000_000_000.0),
    "J": ((2, 1, -2), 1.0), "kJ": ((2, 1, -2), 1000.0),
    "W": ((2, 1, -3), 1.0), "kW": ((2, 1, -3), 1000.0),
    "Hz": ((0, 0, -1), 1.0),
}


def convert_units(value: Any, from_unit: Any, to_unit: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ToolInputError("unit_value_must_be_finite_number")
    if not isinstance(from_unit, str) or not isinstance(to_unit, str):
        raise ToolInputError("unit_names_must_be_strings")
    if from_unit not in _UNITS or to_unit not in _UNITS:
        raise ToolInputError("unsupported_unit")
    source_dim, source_scale = _UNITS[from_unit]
    target_dim, target_scale = _UNITS[to_unit]
    if source_dim != target_dim:
        raise ToolInputError("unit_dimension_mismatch")
    result = float(value) * source_scale / target_scale
    if not math.isfinite(result) or abs(result) > 1e100:
        raise ToolInputError("unit_result_out_of_bounds")
    return result


_ALLOWED_MATH_FUNCTIONS: dict[str, Callable[..., float]] = {
    name: getattr(math, name) for name in
    ("sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "log", "log10", "exp", "fabs")
}
_ALLOWED_MATH_CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}
_ALLOWED_BINOPS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b, ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
}


def evaluate_expression(expression: Any) -> float:
    """Safely evaluate a bounded numeric expression without eval or imports."""
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 2000:
        raise ToolInputError("expression_missing_or_too_long")
    try:
        root = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ToolInputError("expression_syntax_error") from exc
    if sum(1 for _ in ast.walk(root)) > 128:
        raise ToolInputError("expression_complexity_limit")

    def visit(node: ast.AST, depth: int = 0) -> float:
        if depth > 32:
            raise ToolInputError("expression_depth_limit")
        if isinstance(node, ast.Expression):
            return visit(node.body, depth + 1)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            value = float(node.value)
        elif isinstance(node, ast.Name) and node.id in _ALLOWED_MATH_CONSTANTS:
            value = _ALLOWED_MATH_CONSTANTS[node.id]
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = visit(node.operand, depth + 1)
            value = operand if isinstance(node.op, ast.UAdd) else -operand
        elif isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
            left, right = visit(node.left, depth + 1), visit(node.right, depth + 1)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ToolInputError("exponent_limit")
            value = _ALLOWED_BINOPS[type(node.op)](left, right)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_MATH_FUNCTIONS and not node.keywords:
            value = float(_ALLOWED_MATH_FUNCTIONS[node.func.id](*(visit(arg, depth + 1) for arg in node.args)))
        else:
            raise ToolInputError("expression_operation_not_allowed")
        if not math.isfinite(value) or abs(value) > 1e100:
            raise ToolInputError("numeric_result_out_of_bounds")
        return float(value)

    try:
        return visit(root)
    except ToolInputError:
        raise
    except (ArithmeticError, OverflowError, TypeError, ValueError) as exc:
        raise ToolInputError("numeric_evaluation_failed:" + type(exc).__name__) from exc


def solve_linear_system(matrix: Any, vector: Any) -> list[float]:
    """Solve Ax=b with bounded Gauss-Jordan elimination; reject singular systems."""
    if not isinstance(matrix, list) or not isinstance(vector, list) or not matrix or len(matrix) != len(vector):
        raise ToolInputError("linear_system_shape_invalid")
    n = len(matrix)
    if n > 100 or any(not isinstance(row, list) or len(row) != n for row in matrix):
        raise ToolInputError("linear_system_must_be_square_and_at_most_100")
    aug: list[list[float]] = []
    try:
        for row, rhs in zip(matrix, vector):
            values = [float(item) for item in row] + [float(rhs)]
            if not all(math.isfinite(item) for item in values):
                raise ToolInputError("linear_system_values_must_be_finite")
            aug.append(values)
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ToolInputError):
            raise
        raise ToolInputError("linear_system_values_must_be_numeric") from exc
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(aug[row][col]))
        if abs(aug[pivot][col]) <= 1e-12:
            raise ToolInputError("linear_system_singular_or_ill_conditioned")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        divisor = aug[col][col]
        aug[col] = [item / divisor for item in aug[col]]
        for row in range(n):
            if row != col:
                factor = aug[row][col]
                aug[row] = [aug[row][idx] - factor * aug[col][idx] for idx in range(n + 1)]
    solution = [aug[row][n] for row in range(n)]
    if not all(math.isfinite(item) and abs(item) <= 1e100 for item in solution):
        raise ToolInputError("linear_solution_out_of_bounds")
    return solution


class GitHubReadOnlyAdapter:
    """Read-only GitHub contents client; it does not mutate repositories."""

    def __init__(self, *, token: str | None = None, api_base_url: str = "https://api.github.com",
                 open_url: OpenUrl = urllib.request.urlopen, timeout_seconds: float = 10.0) -> None:
        if not _safe_endpoint(api_base_url):
            raise ValueError("github_api_url_must_use_https_or_loopback_http")
        self.api_base_url = api_base_url.rstrip("/")
        self.token = token if token is not None else os.environ.get("VX_GITHUB_TOKEN")
        self.open_url = open_url
        self.timeout_seconds = max(1.0, min(float(timeout_seconds), 20.0))

    def fetch_file(self, arguments: Mapping[str, Any]) -> JSONMap:
        repository, path, ref = arguments.get("repository"), arguments.get("path"), arguments.get("ref")
        if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ToolInputError("github_repository_must_be_owner_slash_repo")
        if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/") or "\\" in path:
            raise ToolInputError("github_path_invalid")
        if ref is not None and (not isinstance(ref, str) or len(ref) > 200):
            raise ToolInputError("github_ref_invalid")
        query = "?" + urllib.parse.urlencode({"ref": ref}) if ref else ""
        encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
        url = f"{self.api_base_url}/repos/{repository}/contents/{encoded_path}{query}"
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "vx-engineering-tools/1.0"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with self.open_url(request, timeout=self.timeout_seconds) as response:
                payload = _read_json_response(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise ToolInputError("github_file_not_found_or_not_visible") from exc
            if exc.code in (401, 403):
                raise ToolInputError("github_access_denied_or_rate_limited") from exc
            raise ToolInputError("github_http_error:" + str(exc.code)) from exc
        except urllib.error.URLError as exc:
            raise ToolInputError("github_network_error") from exc
        content = payload.get("content")
        if payload.get("type") != "file" or payload.get("encoding") != "base64" or not isinstance(content, str):
            raise ToolInputError("github_response_not_a_base64_file")
        try:
            decoded = base64.b64decode(content, validate=False).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ToolInputError("github_file_not_utf8_or_invalid_base64") from exc
        if len(decoded.encode("utf-8")) > 1_500_000:
            raise ToolInputError("github_file_too_large")
        source_url, blob_sha = payload.get("html_url"), payload.get("sha")
        if not isinstance(source_url, str) or not isinstance(blob_sha, str):
            raise ToolInputError("github_response_missing_provenance")
        return {"repository": repository, "path": path, "ref": ref, "content": decoded,
                "blob_sha": blob_sha, "source_url": source_url, "evidence_refs": [source_url]}


class RemoteSandboxAdapter:
    """Adapter for a user-hosted sandbox implementing the VX /v1/execute receipt contract."""

    def __init__(self, *, endpoint: str | None = None, token: str | None = None,
                 open_url: OpenUrl = urllib.request.urlopen, timeout_seconds: float = 65.0) -> None:
        self.endpoint = endpoint if endpoint is not None else os.environ.get("VX_SANDBOX_ENDPOINT")
        self.token = token if token is not None else os.environ.get("VX_SANDBOX_TOKEN")
        self.open_url = open_url
        self.timeout_seconds = max(2.0, min(float(timeout_seconds), 70.0))
        if self.endpoint and not _safe_endpoint(self.endpoint):
            raise ValueError("sandbox_endpoint_must_use_https_or_loopback_http")

    def execute_python(self, arguments: Mapping[str, Any]) -> JSONMap:
        if not self.endpoint:
            raise ToolNotConfigured("sandbox_endpoint_not_configured")
        code, timeout = arguments.get("code"), arguments.get("timeout_seconds", 20)
        if not isinstance(code, str) or not code.strip() or len(code.encode("utf-8")) > 64_000:
            raise ToolInputError("sandbox_code_missing_or_too_large")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 60:
            raise ToolInputError("sandbox_timeout_must_be_1_to_60_seconds")
        body = {"language": "python", "code": code, "timeout_seconds": timeout}
        headers = {"Content-Type": "application/json", "Accept": "application/json",
                   "User-Agent": "vx-engineering-tools/1.0"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = urllib.request.Request(self.endpoint, data=canonical_json(body).encode("utf-8"),
                                         headers=headers, method="POST")
        try:
            with self.open_url(request, timeout=self.timeout_seconds) as response:
                result = _read_json_response(response)
        except urllib.error.HTTPError as exc:
            raise ToolInputError("sandbox_http_error:" + str(exc.code)) from exc
        except urllib.error.URLError as exc:
            raise ToolInputError("sandbox_network_error") from exc
        if not isinstance(result.get("execution_id"), str) or not isinstance(result.get("exit_code"), int):
            raise ToolInputError("sandbox_response_missing_execution_receipt")
        return {"execution_id": result["execution_id"], "exit_code": result["exit_code"],
                "stdout": str(result.get("stdout", ""))[:200_000],
                "stderr": str(result.get("stderr", ""))[:200_000],
                "timed_out": bool(result.get("timed_out", False)),
                "provider_status": result.get("status"),
                "evidence_refs": ["sandbox-execution:" + result["execution_id"]]}


class EngineeringSolverGateway:
    """Gateway contract for external CAD/CAE/CFD and numerical services, not native solver clients."""

    ALLOWED_SOLVERS = {"cadquery", "freecad", "openfoam", "calculix", "gmsh", "fenics", "scipy", "custom"}

    def __init__(self, *, endpoint: str | None = None, token: str | None = None,
                 open_url: OpenUrl = urllib.request.urlopen, timeout_seconds: float = 20.0) -> None:
        self.endpoint = endpoint if endpoint is not None else os.environ.get("VX_ENGINEERING_SOLVER_GATEWAY")
        self.token = token if token is not None else os.environ.get("VX_ENGINEERING_SOLVER_TOKEN")
        self.open_url = open_url
        self.timeout_seconds = max(2.0, min(float(timeout_seconds), 30.0))
        if self.endpoint and not _safe_endpoint(self.endpoint):
            raise ValueError("solver_gateway_must_use_https_or_loopback_http")

    def submit(self, arguments: Mapping[str, Any]) -> JSONMap:
        if not self.endpoint:
            raise ToolNotConfigured("engineering_solver_gateway_not_configured")
        solver, job = arguments.get("solver"), arguments.get("job")
        if not isinstance(solver, str) or solver not in self.ALLOWED_SOLVERS:
            raise ToolInputError("solver_not_allowlisted")
        if not isinstance(job, dict) or len(canonical_json(job).encode("utf-8")) > 512_000:
            raise ToolInputError("solver_job_must_be_json_object_under_512kb")
        request_id = arguments.get("request_id") or sha256_json({"solver": solver, "job": job})[:24]
        body = {"solver": solver, "job": job, "request_id": request_id}
        headers = {"Content-Type": "application/json", "Accept": "application/json",
                   "User-Agent": "vx-engineering-tools/1.0"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = urllib.request.Request(self.endpoint, data=canonical_json(body).encode("utf-8"),
                                         headers=headers, method="POST")
        try:
            with self.open_url(request, timeout=self.timeout_seconds) as response:
                result = _read_json_response(response)
        except urllib.error.HTTPError as exc:
            raise ToolInputError("solver_gateway_http_error:" + str(exc.code)) from exc
        except urllib.error.URLError as exc:
            raise ToolInputError("solver_gateway_network_error") from exc
        job_id, status = result.get("job_id"), result.get("status")
        if not isinstance(job_id, str) or not isinstance(status, str):
            raise ToolInputError("solver_gateway_response_missing_job_receipt")
        return {"solver": solver, "job_id": job_id, "status": status,
                "result_uri": result.get("result_uri"), "evidence_refs": ["solver-job:" + job_id]}


Handler = Callable[[Mapping[str, Any]], Mapping[str, Any]]


class EngineeringToolHub:
    """Tool registry enforcing caller family, authority, capabilities, approvals and evidence hashes."""

    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, Handler] = {}

    def register(self, spec: ToolSpec, handler: Handler) -> None:
        if spec.tool_id in self._specs:
            raise ValueError("tool_id_already_registered:" + spec.tool_id)
        if not spec.tool_id or not spec.version or not callable(handler):
            raise ValueError("tool_identity_and_callable_handler_required")
        self._specs[spec.tool_id] = spec
        self._handlers[spec.tool_id] = handler

    def catalog(self) -> list[JSONMap]:
        return [asdict(self._specs[key]) for key in sorted(self._specs)]

    def invoke(self, tool_id: str, arguments: Mapping[str, Any], *, caller_family: str,
               authority_scope: str, caller_capabilities: tuple[str, ...] = (),
               explicit_approval: bool = False) -> ToolResult:
        spec = self._specs.get(tool_id)
        if spec is None:
            return ToolResult("BLOCKED", tool_id, error_code="tool_not_registered")
        if not isinstance(arguments, Mapping):
            return ToolResult("BLOCKED", tool_id, error_code="arguments_must_be_object")
        try:
            payload_size = len(canonical_json(dict(arguments)).encode("utf-8"))
        except (TypeError, ValueError):
            return ToolResult("BLOCKED", tool_id, error_code="arguments_not_json_serializable")
        if payload_size > spec.max_input_bytes:
            return ToolResult("BLOCKED", tool_id, error_code="tool_input_size_limit")
        if caller_family not in spec.allowed_families:
            return ToolResult("BLOCKED", tool_id, error_code="caller_family_not_authorized")
        if authority_scope not in spec.allowed_scopes:
            return ToolResult("BLOCKED", tool_id, error_code="authority_scope_not_authorized")
        if spec.requires_explicit_approval and not explicit_approval:
            return ToolResult("BLOCKED", tool_id, error_code="explicit_approval_required")
        if spec.required_capabilities and not set(spec.required_capabilities).issubset(set(caller_capabilities)):
            return ToolResult("BLOCKED", tool_id, error_code="required_capability_missing")
        input_hash = sha256_json(dict(arguments))
        try:
            output = dict(self._handlers[tool_id](arguments))
            output_hash = sha256_json(output)
            refs = output.get("evidence_refs", [])
            source_refs = tuple(ref for ref in refs if isinstance(ref, str)) if isinstance(refs, list) else ()
            evidence = ToolEvidence(tool_id, spec.version, input_hash, output_hash, source_refs)
            return ToolResult("COMPLETED", tool_id, output, evidence=evidence)
        except ToolNotConfigured as exc:
            return ToolResult("NOT_CONFIGURED", tool_id, error_code=str(exc))
        except ToolInputError as exc:
            return ToolResult("FAILED", tool_id, error_code=str(exc))
        except Exception as exc:
            return ToolResult("FAILED", tool_id, error_code="adapter_unhandled_error:" + type(exc).__name__)


def build_engineering_tool_hub(*, environ: Mapping[str, str] | None = None,
                               open_url: OpenUrl = urllib.request.urlopen) -> EngineeringToolHub:
    """Create the catalog; remote integrations stay NOT_CONFIGURED until explicitly bound."""
    env = dict(os.environ if environ is None else environ)
    hub = EngineeringToolHub()
    hub.register(ToolSpec("math.evaluate", "1.0.0", "Safely evaluate a bounded numeric expression.",
                          ("analysis", "research", "verification"), required_capabilities=("math_evaluation",)),
                 lambda args: {"value": evaluate_expression(args.get("expression"))})
    hub.register(ToolSpec("math.solve_linear_system", "1.0.0", "Solve a finite square linear system.",
                          ("analysis", "research", "verification"), required_capabilities=("linear_algebra",)),
                 lambda args: {"solution": solve_linear_system(args.get("matrix"), args.get("vector"))})
    hub.register(ToolSpec("engineering.convert_units", "1.0.0", "Convert SI-derived units with dimension checks.",
                          ("analysis", "research", "verification"), required_capabilities=("unit_conversion",)),
                 lambda args: {"value": convert_units(args.get("value"), args.get("from_unit"), args.get("to_unit")),
                               "from_unit": args.get("from_unit"), "to_unit": args.get("to_unit")})
    github = GitHubReadOnlyAdapter(token=env.get("VX_GITHUB_TOKEN"),
                                   api_base_url=env.get("VX_GITHUB_API_BASE_URL", "https://api.github.com"),
                                   open_url=open_url)
    hub.register(ToolSpec("github.fetch_file", "1.0.0", "Fetch a UTF-8 GitHub file read-only with blob SHA and source URL.",
                          ("read-only", "research", "analysis", "verification"), max_input_bytes=10_000),
                 github.fetch_file)
    sandbox = RemoteSandboxAdapter(endpoint=env.get("VX_SANDBOX_ENDPOINT"), token=env.get("VX_SANDBOX_TOKEN"),
                                   open_url=open_url)
    hub.register(ToolSpec("sandbox.execute_python", "1.0.0", "Request bounded Python execution through a configured sandbox gateway.",
                          ("sandbox",), allowed_families=("engineering", "governance"),
                          requires_explicit_approval=True, max_input_bytes=70_000), sandbox.execute_python)
    solver = EngineeringSolverGateway(endpoint=env.get("VX_ENGINEERING_SOLVER_GATEWAY"),
                                      token=env.get("VX_ENGINEERING_SOLVER_TOKEN"), open_url=open_url)
    hub.register(ToolSpec("engineering.solver.submit", "1.0.0", "Submit a job to a configured CAD/CAE/CFD solver gateway.",
                          ("sandbox", "sandbox-write"), allowed_families=("engineering", "governance"),
                          requires_explicit_approval=True, max_input_bytes=520_000), solver.submit)
    return hub
