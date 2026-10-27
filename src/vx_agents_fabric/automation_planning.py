"""Offline Zapier handoff compiler; no account connection or action invocation."""
from __future__ import annotations
import re
from typing import Any, Mapping
from .contracts import content_hash


def compile_zapier_handoff(arguments: Mapping[str, Any]) -> dict[str, Any]:
    required = {'workflow_id','simulation_plan_sha256','target_app','action_name','artifact_refs'}
    if not isinstance(arguments, Mapping) or set(arguments) != required:
        raise ValueError('invalid_zapier_handoff_envelope')
    for field in ('workflow_id','target_app','action_name'):
        value=arguments[field]
        if not isinstance(value,str) or not value.strip() or len(value)>128:
            raise ValueError('invalid_'+field)
    digest=arguments['simulation_plan_sha256']
    if not isinstance(digest,str) or not re.fullmatch('[a-f0-9]{64}',digest):
        raise ValueError('invalid_simulation_plan_digest')
    refs=arguments['artifact_refs']
    if not isinstance(refs,list) or not 1<=len(refs)<=32 or any(not isinstance(r,str) or not r.strip() or len(r)>256 for r in refs):
        raise ValueError('invalid_artifact_refs')
    if len(set(refs)) != len(refs):
        raise ValueError('duplicate_artifact_refs')
    intent={**arguments,'artifact_refs':sorted(refs)}
    return {'schema_version':'1.0.0','status':'PENDING_AUTHORIZATION',
            'handoff_sha256':content_hash(intent),'idempotency_key':content_hash(intent),
            'intent':intent,'connection':'NOT_CONFIGURED',
            'artifact_integrity':'NOT_CHECKED','action_catalog_validation':'NOT_PERFORMED',
            'payload_transfer':'NONE','execution_performed':False,'production_gate':'HOLD',
            'required_gates':['authenticated_zapier_account','fixed_tool_allowlist',
                              'artifact_integrity_and_data_scope','independent_action_approval',
                              'task_quota_and_spend_authority','durable_idempotency',
                              'action_receipt_and_independent_verification'],
            'prohibited_implicit_actions':['send_message','publish','payment','trade','deploy'],
            'external_spend_sar':0,'evidence_refs':[]}
