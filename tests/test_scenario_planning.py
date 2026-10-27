import copy
from dataclasses import replace
import unittest

from vx_agents_fabric.scenario_planning import compile_scenario_plan, ScenarioPlanError
from vx_agents_fabric.registry import default_registry
from vx_agents_fabric.engineering_tools import build_engineering_tool_hub, bind_registered_agent_tool_dispatcher


def sample():
    return {'scenario_id':'launch-001', 'question':'How might customers react to a service change?',
        'sources':[{'source_id':'s1','root_id':'study-001','sha256':'a'*64}],
        'actors':[{'actor_id':'customer','role':'Customer perspective','source_ids':['s1']}],
        'interventions':[{'intervention_id':'simpler-booking','description':'Reduce booking steps','source_ids':['s1']}],
        'seed':7, 'max_agents':10, 'max_rounds':5}


class ScenarioPlanningTests(unittest.TestCase):
    def test_plan_has_baseline_and_intervention_but_no_predicted_outcome(self):
        plan = compile_scenario_plan(sample())
        self.assertEqual([v['variant_id'] for v in plan['variants']], ['baseline','simpler-booking'])
        self.assertTrue(all(v['state']=='NOT_RUN' for v in plan['variants']))
        self.assertFalse(plan['execution_performed'])
        self.assertEqual(plan['production_gate'],'HOLD')
        self.assertEqual(plan['source_independence'],'NOT_VERIFIED')
        self.assertEqual(plan['evidence_refs'], [])

    def test_repeatable_and_input_not_mutated(self):
        data=sample(); before=copy.deepcopy(data)
        self.assertEqual(compile_scenario_plan(data), compile_scenario_plan(data))
        self.assertEqual(data,before)
        changed={**data,'seed':8}
        self.assertNotEqual(compile_scenario_plan(data)['plan_sha256'], compile_scenario_plan(changed)['plan_sha256'])

    def test_source_and_actor_order_do_not_change_fingerprint(self):
        data=sample()
        data['sources'].append({'source_id':'s2','root_id':'study-002','sha256':'b'*64})
        data['actors'].append({'actor_id':'operator','role':'Operations','source_ids':['s2']})
        before=compile_scenario_plan(data)['plan_sha256']
        data['sources'].reverse(); data['actors'].reverse()
        self.assertEqual(before, compile_scenario_plan(data)['plan_sha256'])

    def test_repeated_reports_share_declared_root_and_gain_no_independent_evidence(self):
        data=sample();data['sources'].append({'source_id':'summary','root_id':'study-001','sha256':'b'*64})
        plan=compile_scenario_plan(data)
        self.assertEqual(plan['source_root_groups'],{'study-001':['s1','summary']})
        self.assertEqual(plan['source_independence'],'NOT_VERIFIED')

    def test_identical_content_cannot_claim_distinct_roots(self):
        data=sample();data['sources'].append({'source_id':'copy','root_id':'other-root','sha256':'a'*64})
        with self.assertRaisesRegex(ScenarioPlanError,'conflicting_roots'):
            compile_scenario_plan(data)

    def test_invalid_boundaries_and_unexpected_fields_rejected(self):
        for changes in [dict(max_rounds=True),dict(max_agents=0),dict(max_rounds=41),dict(seed=-1),dict(execute=True),dict(question=''),dict(sources=[]),dict(actors=[])]:
            with self.subTest(changes=changes),self.assertRaises(ScenarioPlanError):
                compile_scenario_plan({**sample(),**changes})

    def test_unknown_source_duplicate_actor_and_reserved_variant_rejected(self):
        for kind in ('unknown','duplicate','reserved'):
            data=sample()
            if kind=='unknown': data['actors'][0]['source_ids']=['invented']
            if kind=='duplicate': data['actors'].append(copy.deepcopy(data['actors'][0]))
            if kind=='reserved': data['interventions'][0]['intervention_id']='baseline'
            with self.subTest(kind=kind),self.assertRaises(ScenarioPlanError):compile_scenario_plan(data)

    def test_empty_interventions_produce_baseline_only(self):
        data=sample();data['interventions']=[]
        self.assertEqual(len(compile_scenario_plan(data)['variants']),1)


class ScenarioVXBindingTests(unittest.TestCase):
    def setUp(self):
        self.hub=build_engineering_tool_hub(environ={},open_url=lambda *a,**kw: self.fail('network not permitted'))
        self.registry=default_registry()

    def test_specialist_is_registered_but_not_self_admitted(self):
        spec=self.registry.resolve('VX-SIM-PLAN')
        self.assertEqual(spec.admission_status,'DESIGN_ONLY')
        with self.assertRaises(PermissionError):
            bind_registered_agent_tool_dispatcher(self.hub,self.registry,spec.role_id,allowed_tool_ids=('simulation.plan_scenarios',))

    def test_admitted_test_fixture_routes_through_real_vx_gate_and_hash_receipts(self):
        # Admission is synthetic fixture data, not production governance.
        spec=replace(self.registry.resolve('VX-SIM-PLAN'),version='1.0.1',admission_status='ADMITTED')
        self.registry.register(spec)
        dispatcher=bind_registered_agent_tool_dispatcher(self.hub,self.registry,spec.role_id,role_version='1.0.1',allowed_tool_ids=('simulation.plan_scenarios',))
        result=dispatcher.invoke('simulation.plan_scenarios',sample())
        self.assertEqual(result.status,'COMPLETED')
        self.assertEqual(result.result['status'],'PLANNED')
        self.assertFalse(result.result['execution_performed'])
        self.assertEqual(result.control_decision['decision'],'ALLOW')
        self.assertTrue(dispatcher.control_gate.verify_event_chain())
        rejected=dispatcher.invoke('sandbox.execute_python',{'code':'print(1)'})
        self.assertEqual(rejected.status,'BLOCKED')

    def test_existing_agent_without_capability_cannot_use_planner(self):
        result=self.hub.invoke('simulation.plan_scenarios',sample(),caller_family='engineering',authority_scope='planning')
        self.assertEqual(result.status,'BLOCKED')
        self.assertEqual(result.error_code,'required_capability_missing')

    def test_invalid_plan_is_failure_not_fake_completion(self):
        result=self.hub.invoke('simulation.plan_scenarios',{'execute':True},caller_family='engineering',authority_scope='planning',caller_capabilities=('scenario_planning',))
        self.assertEqual(result.status,'FAILED')
