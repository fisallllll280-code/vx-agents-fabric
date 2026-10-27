from dataclasses import replace
import unittest
from vx_agents_fabric.automation_planning import compile_zapier_handoff
from vx_agents_fabric.engineering_tools import build_engineering_tool_hub, bind_registered_agent_tool_dispatcher
from vx_agents_fabric.registry import default_registry


def sample():
    return {'workflow_id':'wf-001','simulation_plan_sha256':'a'*64,
            'target_app':'project-tracker','action_name':'create_review_task',
            'artifact_refs':['artifact:plan-001','artifact:review-001']}


class ZapierHandoffTests(unittest.TestCase):
    def test_handoff_is_pending_not_executed_or_connected(self):
        result=compile_zapier_handoff(sample())
        self.assertEqual(result['status'],'PENDING_AUTHORIZATION')
        self.assertFalse(result['execution_performed'])
        self.assertEqual(result['connection'],'NOT_CONFIGURED')
        self.assertEqual(result['evidence_refs'],[])
        self.assertIn('independent_action_approval',result['required_gates'])

    def test_reordered_refs_replay_same_intent_digest(self):
        data=sample();a=compile_zapier_handoff(data)
        data['artifact_refs'].reverse()
        self.assertEqual(a,compile_zapier_handoff(data))
        data['action_name']='different_action'
        self.assertNotEqual(a['idempotency_key'],compile_zapier_handoff(data)['idempotency_key'])

    def test_secrets_payload_execute_or_missing_fields_rejected(self):
        for changes in [dict(execute=True),dict(token='secret'),dict(payload={'private':'data'}),dict(simulation_plan_sha256='bad'),dict(action_name=''),dict(artifact_refs=[])]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                compile_zapier_handoff({**sample(),**changes})

    def test_default_role_cannot_self_admit(self):
        hub=build_engineering_tool_hub(environ={})
        registry=default_registry()
        with self.assertRaises(PermissionError):
            bind_registered_agent_tool_dispatcher(hub,registry,'VX-AUTO-ZAPIER',allowed_tool_ids=('automation.plan_zapier',))

    def test_test_fixture_calls_planner_through_vx_without_network(self):
        hub=build_engineering_tool_hub(environ={},open_url=lambda *a,**kw: self.fail('no network'))
        registry=default_registry()
        spec=replace(registry.resolve('VX-AUTO-ZAPIER'),version='1.0.1',admission_status='ADMITTED')
        registry.register(spec)
        dispatcher=bind_registered_agent_tool_dispatcher(hub,registry,spec.role_id,role_version='1.0.1',allowed_tool_ids=('automation.plan_zapier',))
        result=dispatcher.invoke('automation.plan_zapier',sample())
        self.assertEqual(result.status,'COMPLETED')
        self.assertFalse(result.result['execution_performed'])
        self.assertTrue(dispatcher.control_gate.verify_event_chain())
        self.assertEqual(dispatcher.invoke('simulation.plan_scenarios',{}).status,'BLOCKED')

    def test_missing_capability_blocked(self):
        hub=build_engineering_tool_hub(environ={})
        result=hub.invoke('automation.plan_zapier',sample(),caller_family='engineering',authority_scope='planning')
        self.assertEqual(result.error_code,'required_capability_missing')
