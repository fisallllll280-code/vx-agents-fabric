"""Contract, policy, and no-network tests for engineering tool integrations."""
from __future__ import annotations

import base64
import json
import unittest
from datetime import datetime, timedelta, timezone

from vx_agents_fabric.contracts import AgentSpec
from vx_agents_fabric.registry import AgentRegistry, default_registry
from vx_agents_fabric.engineering_tools import (
    BoundEngineeringToolDispatcher,
    bind_registered_agent_tool_dispatcher,
    ToolAccessPolicy,
    GitHubReadOnlyAdapter,
    build_engineering_tool_hub,
    convert_units,
    evaluate_expression,
    solve_linear_system,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self.payload if size < 0 else self.payload[:size]


class EngineeringMathTests(unittest.TestCase):
    def test_safe_expression(self):
        self.assertAlmostEqual(evaluate_expression("sqrt(9) + 2*pi"), 3 + 2 * 3.141592653589793)

    def test_expression_rejects_imports_attributes_and_large_exponents(self):
        for expr in ("__import__('os').system('echo unsafe')", "math.sqrt(4)", "open('x')", "2 ** 101"):
            with self.subTest(expr=expr), self.assertRaises(ValueError):
                evaluate_expression(expr)

    def test_division_by_zero_returns_a_controlled_error(self):
        with self.assertRaisesRegex(ValueError, "numeric_evaluation_failed"):
            evaluate_expression("1 / 0")

    def test_unit_conversion_and_dimension_guard(self):
        self.assertAlmostEqual(convert_units(36, "km/h", "m/s"), 10)
        with self.assertRaisesRegex(ValueError, "dimension_mismatch"):
            convert_units(1, "m", "kg")

    def test_linear_system(self):
        answer = solve_linear_system([[2, 1], [1, -1]], [5, 1])
        self.assertAlmostEqual(answer[0], 2)
        self.assertAlmostEqual(answer[1], 1)

    def test_singular_system_rejected(self):
        with self.assertRaisesRegex(ValueError, "singular"):
            solve_linear_system([[1, 2], [2, 4]], [3, 6])


class ToolHubPolicyTests(unittest.TestCase):
    def setUp(self):
        self.hub = build_engineering_tool_hub(environ={})

    def test_completed_tool_has_hash_evidence(self):
        result = self.hub.invoke(
            "math.evaluate", {"expression": "sqrt(16)"},
            caller_family="engineering", authority_scope="analysis",
            caller_capabilities=("math_evaluation",))
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.result["value"], 4.0)
        self.assertEqual(len(result.evidence.input_sha256), 64)
        self.assertEqual(len(result.evidence.output_sha256), 64)

    def test_scope_and_capability_fail_closed(self):
        denied = self.hub.invoke(
            "math.evaluate", {"expression": "1+1"},
            caller_family="engineering", authority_scope="production",
            caller_capabilities=("math_evaluation",))
        self.assertEqual(denied.status, "BLOCKED")
        missing = self.hub.invoke(
            "math.evaluate", {"expression": "1+1"},
            caller_family="engineering", authority_scope="analysis")
        self.assertEqual(missing.error_code, "required_capability_missing")

    def test_solver_submit_requires_explicit_approval(self):
        result = self.hub.invoke(
            "engineering.solver.submit", {"solver": "openfoam", "job": {}},
            caller_family="engineering", authority_scope="sandbox")
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.error_code, "explicit_approval_required")

    def test_unconfigured_integrations_never_claim_success(self):
        sandbox = self.hub.invoke(
            "sandbox.execute_python", {"code": "print(1)"},
            caller_family="engineering", authority_scope="sandbox", explicit_approval=True)
        solver = self.hub.invoke(
            "engineering.solver.submit", {"solver": "openfoam", "job": {}},
            caller_family="engineering", authority_scope="sandbox", explicit_approval=True)
        self.assertEqual(sandbox.status, "NOT_CONFIGURED")
        self.assertEqual(solver.status, "NOT_CONFIGURED")

    def test_unknown_tool_and_wrong_family_are_blocked(self):
        unknown = self.hub.invoke("not.registered", {}, caller_family="engineering", authority_scope="analysis")
        self.assertEqual(unknown.error_code, "tool_not_registered")
        wrong_family = self.hub.invoke(
            "sandbox.execute_python", {"code": "print(1)"},
            caller_family="research", authority_scope="sandbox", explicit_approval=True)
        self.assertEqual(wrong_family.error_code, "caller_family_not_authorized")

    def test_catalog_is_stable_and_provider_neutral(self):
        ids = {item["tool_id"] for item in self.hub.catalog()}
        self.assertTrue({
            "github.fetch_file", "sandbox.execute_python", "engineering.solver.submit",
            "math.evaluate", "math.solve_linear_system", "engineering.convert_units",
        }.issubset(ids))


    def test_dispatcher_emits_vx_decision_and_hash_chained_receipt(self):
        policy = ToolAccessPolicy(
            role_id="VX-ENG-TEST", role_version="1.0.0",
            caller_family="engineering", authority_scope="analysis",
            capabilities=("math_evaluation",),
            allowed_tool_ids=("math.evaluate",),
        )
        dispatcher = BoundEngineeringToolDispatcher(self.hub, policy)
        result = dispatcher.invoke("math.evaluate", {"expression": "6*7"})
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.control_decision["gate"], "VX_FEDERATION_GATE")
        self.assertEqual(result.control_decision["decision"], "ALLOW")
        self.assertEqual(result.control_decision["execution_status"], "COMPLETED")
        self.assertEqual(len(dispatcher.control_events), 1)
        event = dispatcher.control_events[0]
        self.assertEqual(event["execution_status"], "COMPLETED")
        self.assertEqual(event["previous_event_sha256"], "0" * 64)
        self.assertEqual(len(event["event_sha256"]), 64)
        self.assertNotIn("arguments", event)
        self.assertTrue(dispatcher.control_gate.verify_event_chain())

    def test_dispatcher_budget_stops_additional_tool_calls(self):
        policy = ToolAccessPolicy(
            role_id="VX-ENG-TEST", role_version="1.0.0",
            caller_family="engineering", authority_scope="analysis",
            capabilities=("math_evaluation",),
            allowed_tool_ids=("math.evaluate",),
            max_tool_calls=1,
        )
        dispatcher = BoundEngineeringToolDispatcher(self.hub, policy)
        first = dispatcher.invoke("math.evaluate", {"expression": "2+2"})
        second = dispatcher.invoke("math.evaluate", {"expression": "3+3"})
        self.assertEqual(first.status, "COMPLETED")
        self.assertEqual(second.status, "BLOCKED")
        self.assertEqual(second.error_code, "vx_budget_tool_call_limit")
        self.assertEqual(second.control_decision["execution_status"], "NOT_EXECUTED")
        self.assertEqual(len(dispatcher.control_events), 2)
        self.assertTrue(dispatcher.control_gate.verify_event_chain())

    def test_emergency_stop_blocks_bound_tool_before_execution(self):
        policy = ToolAccessPolicy(
            role_id="VX-ENG-TEST", role_version="1.0.0",
            caller_family="engineering", authority_scope="analysis",
            capabilities=("math_evaluation",),
            allowed_tool_ids=("math.evaluate",),
        )
        dispatcher = BoundEngineeringToolDispatcher(self.hub, policy)
        dispatcher.activate_emergency_stop("test_stop")
        result = dispatcher.invoke("math.evaluate", {"expression": "2+2"})
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.control_decision["decision"], "REJECT")
        self.assertEqual(result.error_code, "emergency_stop_active:test_stop")
        self.assertEqual(result.control_decision["execution_status"], "NOT_EXECUTED")
        with self.assertRaisesRegex(PermissionError, "authorized_operator"):
            dispatcher.clear_emergency_stop(authorized=False)
        self.assertTrue(dispatcher.control_gate.verify_event_chain())

    def test_dispatcher_rejects_unbounded_host_policy(self):
        policy = ToolAccessPolicy(
            role_id="VX-ENG-TEST", role_version="1.0.0",
            caller_family="engineering", authority_scope="analysis",
            capabilities=("math_evaluation",),
            allowed_tool_ids=("math.evaluate",),
            max_tool_calls=257,
        )
        with self.assertRaisesRegex(ValueError, "max_tool_calls_out_of_hard_bounds"):
            BoundEngineeringToolDispatcher(self.hub, policy)


    def test_only_admitted_registry_roles_can_receive_tool_dispatchers(self):
        registry = default_registry()
        with self.assertRaisesRegex(PermissionError, "agent_not_admitted_for_tool_access"):
            bind_registered_agent_tool_dispatcher(
                self.hub, registry, "VX-ENG-TEST", allowed_tool_ids=("math.evaluate",)
            )

    def test_admitted_registry_role_is_bound_to_vx_gate(self):
        spec = AgentSpec(
            role_id="VX-ENG-MATH-TEST",
            name="Admitted math tool test role",
            family="engineering",
            version="1.0.0",
            capabilities=("math_evaluation",),
            inputs=("expression",),
            outputs=("numeric_result",),
            authority_scope="analysis",
            admission_status="ADMITTED",
        )
        registry = AgentRegistry()
        registry.register(spec)
        dispatcher = bind_registered_agent_tool_dispatcher(
            self.hub, registry, spec.role_id,
            allowed_tool_ids=("math.evaluate",),
        )
        result = dispatcher.invoke("math.evaluate", {"expression": "40+2"})
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.result["value"], 42.0)
        self.assertEqual(result.control_decision["gate"], "VX_FEDERATION_GATE")
        self.assertEqual(result.control_decision["actor"]["role_id"], spec.role_id)

    def test_agent_factory_rejects_unregistered_tool_names(self):
        spec = AgentSpec(
            role_id="VX-ENG-MATH-TEST",
            name="Admitted math tool test role",
            family="engineering",
            version="1.0.0",
            capabilities=("math_evaluation",),
            inputs=("expression",),
            outputs=("numeric_result",),
            authority_scope="analysis",
            admission_status="ADMITTED",
        )
        registry = AgentRegistry()
        registry.register(spec)
        with self.assertRaisesRegex(ValueError, "unregistered_tools"):
            bind_registered_agent_tool_dispatcher(
                self.hub, registry, spec.role_id, allowed_tool_ids=("shell.unrestricted",)
            )


    def test_sensitive_tool_approval_is_bound_to_exact_action_digest(self):
        policy = ToolAccessPolicy(
            role_id="VX-ENG-BUILD", role_version="1.0.0",
            caller_family="engineering", authority_scope="sandbox",
            capabilities=(),
            allowed_tool_ids=("sandbox.execute_python",),
            explicitly_approved_tool_ids=("sandbox.execute_python",),
        )

        def verify_signature(record, context):
            # Test verifier only. Production must validate a real signed approval from a trusted authority.
            return record.get("signature") == "valid-test-signature" and (
                record.get("approved_action_digest") == context.get("action_digest")
            )

        dispatcher = BoundEngineeringToolDispatcher(
            self.hub, policy, approval_verifier=verify_signature
        )
        arguments = {"code": "print(1)"}
        prepared = dispatcher.prepare_action("sandbox.execute_python", arguments)
        approval = {
            "status": "APPROVED",
            "approved_action_digest": prepared["action_digest"],
            "action_id": prepared["action_id"],
            "tool_id": prepared["tool_id"],
            "tool_version": prepared["tool_version"],
            "role_id": prepared["actor"]["role_id"],
            "role_version": prepared["actor"]["role_version"],
            "authority_scope": prepared["scope"],
            "policy_digest": prepared["policy_digest"],
            "input_sha256": prepared["input_sha256"],
            "idempotency_key": prepared["idempotency_key"],
            "valid_until": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "approver_id": "human:independent-reviewer",
            "independent": True,
            "signature": "valid-test-signature",
        }
        result = dispatcher.invoke(
            "sandbox.execute_python", arguments, approval_record=approval
        )
        self.assertEqual(result.status, "NOT_CONFIGURED")
        self.assertEqual(result.control_decision["decision"], "ALLOW")
        self.assertEqual(result.control_decision["execution_status"], "NOT_CONFIGURED")
        self.assertTrue(dispatcher.control_gate.verify_event_chain())

    def test_sensitive_tool_approval_cannot_be_reused_for_changed_inputs(self):
        policy = ToolAccessPolicy(
            role_id="VX-ENG-BUILD", role_version="1.0.0",
            caller_family="engineering", authority_scope="sandbox",
            capabilities=(),
            allowed_tool_ids=("sandbox.execute_python",),
            explicitly_approved_tool_ids=("sandbox.execute_python",),
        )
        dispatcher = BoundEngineeringToolDispatcher(
            self.hub, policy,
            approval_verifier=lambda record, context: record.get("signature") == "valid-test-signature",
        )
        prepared = dispatcher.prepare_action(
            "sandbox.execute_python", {"code": "print(1)"}
        )
        approval = {
            "status": "APPROVED",
            "approved_action_digest": prepared["action_digest"],
            "action_id": prepared["action_id"],
            "tool_id": prepared["tool_id"],
            "tool_version": prepared["tool_version"],
            "role_id": prepared["actor"]["role_id"],
            "role_version": prepared["actor"]["role_version"],
            "authority_scope": prepared["scope"],
            "policy_digest": prepared["policy_digest"],
            "input_sha256": prepared["input_sha256"],
            "idempotency_key": prepared["idempotency_key"],
            "valid_until": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "approver_id": "human:independent-reviewer",
            "independent": True,
            "signature": "valid-test-signature",
        }
        result = dispatcher.invoke(
            "sandbox.execute_python", {"code": "print(2)"}, approval_record=approval
        )
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.error_code, "explicit_approval_required")
        self.assertEqual(result.control_decision["execution_status"], "NOT_EXECUTED")

    def test_tool_id_allowlist_alone_is_not_sensitive_action_approval(self):
        policy = ToolAccessPolicy(
            role_id="VX-ENG-BUILD", role_version="1.0.0",
            caller_family="engineering", authority_scope="sandbox",
            capabilities=(),
            allowed_tool_ids=("sandbox.execute_python",),
            explicitly_approved_tool_ids=("sandbox.execute_python",),
        )
        dispatcher = BoundEngineeringToolDispatcher(self.hub, policy)
        result = dispatcher.invoke(
            "sandbox.execute_python", {"code": "print(7)"}
        )
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.error_code, "explicit_approval_required")


class GitHubAdapterTests(unittest.TestCase):
    def test_fetch_file_returns_content_blob_sha_and_source_url(self):
        raw = "# engineering spec\npass\n"
        payload = {
            "type": "file", "encoding": "base64",
            "content": base64.b64encode(raw.encode()).decode(),
            "sha": "abc123",
            "html_url": "https://github.com/org/repo/blob/main/spec.md",
        }
        observed = {}

        def fake_open(request, timeout=10):
            observed["url"] = request.full_url
            observed["method"] = request.get_method()
            return FakeResponse(payload)

        adapter = GitHubReadOnlyAdapter(
            token="test-token", api_base_url="https://api.github.com", open_url=fake_open)
        result = adapter.fetch_file({"repository": "org/repo", "path": "docs/spec.md", "ref": "main"})
        self.assertEqual(result["content"], raw)
        self.assertEqual(result["blob_sha"], "abc123")
        self.assertEqual(observed["method"], "GET")
        self.assertIn("ref=main", observed["url"])

    def test_path_traversal_rejected_before_network(self):
        adapter = GitHubReadOnlyAdapter(open_url=lambda *_a, **_k: self.fail("network must not run"))
        with self.assertRaisesRegex(ValueError, "path_invalid"):
            adapter.fetch_file({"repository": "org/repo", "path": "../secrets"})

    def test_non_tls_public_endpoint_rejected(self):
        with self.assertRaisesRegex(ValueError, "must_use_https"):
            GitHubReadOnlyAdapter(api_base_url="http://api.github.com")


class BoundDispatcherTests(unittest.TestCase):
    def setUp(self):
        self.hub = build_engineering_tool_hub(environ={})

    def test_dispatcher_binds_role_and_capabilities_outside_the_model(self):
        policy = ToolAccessPolicy(
            role_id="VX-ENG-TEST", role_version="1.0.0",
            caller_family="engineering", authority_scope="analysis",
            capabilities=("math_evaluation",),
            allowed_tool_ids=("math.evaluate",),
        )
        dispatcher = BoundEngineeringToolDispatcher(self.hub, policy)
        result = dispatcher.invoke("math.evaluate", {"expression": "3*7"})
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.result["value"], 21.0)

    def test_dispatcher_blocks_tools_not_allowlisted_for_role(self):
        policy = ToolAccessPolicy(
            role_id="VX-ENG-TEST", role_version="1.0.0",
            caller_family="engineering", authority_scope="analysis",
            capabilities=("math_evaluation",),
            allowed_tool_ids=("math.evaluate",),
        )
        result = BoundEngineeringToolDispatcher(self.hub, policy).invoke(
            "engineering.solver.submit", {"solver": "openfoam", "job": {}})
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.error_code, "tool_not_in_role_allowlist")

    def test_approval_is_pinned_in_host_policy(self):
        policy = ToolAccessPolicy(
            role_id="VX-ENG-BUILD", role_version="1.0.0",
            caller_family="engineering", authority_scope="sandbox",
            capabilities=(), allowed_tool_ids=("sandbox.execute_python",),
        )
        result = BoundEngineeringToolDispatcher(self.hub, policy).invoke(
            "sandbox.execute_python", {"code": "print(3)"})
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.error_code, "explicit_approval_required")


if __name__ == "__main__":
    unittest.main(verbosity=2)
