"""Offline scenario-plan compiler inspired by MiroFish's published workflow.

No MiroFish code, network client, simulation engine, grant issuer or prediction.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from .contracts import content_hash


class ScenarioPlanError(ValueError):
    pass


def _text(value: Any, field: str, limit: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ScenarioPlanError('invalid_' + field)
    return value


def _identifier(value: Any, field: str) -> str:
    value = _text(value, field, 128)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', value):
        raise ScenarioPlanError('invalid_' + field)
    return value


def _bounded_int(value: Any, field: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ScenarioPlanError('invalid_' + field)
    return value


def compile_scenario_plan(arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Compile source-linked actor/variant plans without running any agent."""
    required = {'scenario_id', 'question', 'sources', 'actors', 'interventions'}
    optional = {'max_agents', 'max_rounds', 'seed'}
    if not isinstance(arguments, Mapping) or not required <= set(arguments) or set(arguments) - required - optional:
        raise ScenarioPlanError('invalid_plan_envelope')
    scenario_id = _identifier(arguments['scenario_id'], 'scenario_id')
    question = _text(arguments['question'], 'question')
    max_agents = _bounded_int(arguments.get('max_agents', 20), 'max_agents', 1, 40)
    max_rounds = _bounded_int(arguments.get('max_rounds', 10), 'max_rounds', 1, 40)
    seed = _bounded_int(arguments.get('seed', 0), 'seed', 0, 2**32-1)
    sources, actors, interventions = (arguments[k] for k in ('sources', 'actors', 'interventions'))
    if not isinstance(sources, list) or not 1 <= len(sources) <= 100:
        raise ScenarioPlanError('invalid_sources')
    if not isinstance(actors, list) or not 1 <= len(actors) <= max_agents:
        raise ScenarioPlanError('invalid_actors')
    if not isinstance(interventions, list) or len(interventions) > 8:
        raise ScenarioPlanError('invalid_interventions')
    source_map = {}
    root_groups: dict[str, list[str]] = {}
    digest_roots: dict[str, set[str]] = {}
    for source in sources:
        if not isinstance(source, dict) or set(source) != {'source_id', 'root_id', 'sha256'}:
            raise ScenarioPlanError('invalid_source_record')
        source_id = _identifier(source['source_id'], 'source_id')
        root_id = _identifier(source['root_id'], 'root_id')
        if not isinstance(source['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', source['sha256']):
            raise ScenarioPlanError('invalid_source_digest')
        if source_id in source_map:
            raise ScenarioPlanError('duplicate_source_id')
        source_map[source_id] = dict(source)
        root_groups.setdefault(root_id, []).append(source_id)
        digest_roots.setdefault(source['sha256'], set()).add(root_id)
    # Identical content cannot be presented as different independent source roots.
    if any(len(roots) > 1 for roots in digest_roots.values()):
        raise ScenarioPlanError('identical_content_conflicting_roots')

    def records(items: list, id_field: str, text_field: str) -> list[dict]:
        normalized = []
        seen = set()
        for item in items:
            if not isinstance(item, dict) or set(item) != {id_field, text_field, 'source_ids'}:
                raise ScenarioPlanError('invalid_' + id_field + '_record')
            ident = _identifier(item[id_field], id_field)
            if ident in seen or (id_field == 'intervention_id' and ident == 'baseline'):
                raise ScenarioPlanError('duplicate_or_reserved_' + id_field)
            seen.add(ident)
            text = _text(item[text_field], text_field)
            refs = item['source_ids']
            if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) for ref in refs):
                raise ScenarioPlanError('invalid_source_refs')
            if len(set(refs)) != len(refs) or not set(refs) <= set(source_map):
                raise ScenarioPlanError('unknown_or_duplicate_source_ref')
            normalized.append({id_field:ident, text_field:text, 'source_ids':sorted(refs)})
        return sorted(normalized, key=lambda row: row[id_field])

    actor_rows = records(actors, 'actor_id', 'role')
    intervention_rows = records(interventions, 'intervention_id', 'description')
    source_rows = [source_map[key] for key in sorted(source_map)]
    experiment = {'scenario_id':scenario_id, 'question':question, 'sources':source_rows,
                  'actors':actor_rows, 'interventions':intervention_rows,
                  'max_agents':max_agents, 'max_rounds':max_rounds, 'seed':seed}
    digest = content_hash(experiment)
    return {
        'schema_version':'1.0.0', 'status':'PLANNED', 'scenario_id':scenario_id,
        'plan_sha256':digest, 'experiment':experiment,
        'source_root_groups':{key:sorted(root_groups[key]) for key in sorted(root_groups)},
        'source_integrity':'DECLARED_DIGESTS_NOT_CHECKED',
        'source_independence':'NOT_VERIFIED',
        'variants':[{'variant_id':'baseline', 'intervention':None, 'state':'NOT_RUN'}] + [
            {'variant_id':row['intervention_id'], 'intervention':row, 'state':'NOT_RUN'}
            for row in intervention_rows],
        'controls':{'same_seed_per_variant':True, 'reset_memory_per_variant':True,
                    'model_revision':'REQUIRED_BEFORE_EXECUTION'},
        'report_obligations':['compare_baseline_and_each_intervention', 'preserve_source_roots',
                              'label_outputs_as_simulated', 'record_model_and_environment',
                              'independent_real_world_validation_required'],
        'execution_performed':False, 'external_spend_sar':0,
        'simulation_status':'NOT_RUN', 'mirofish_connection':'NOT_CONFIGURED',
        'independent_verification':'NOT_RUN', 'production_gate':'HOLD',
        'evidence_refs':[],
    }
