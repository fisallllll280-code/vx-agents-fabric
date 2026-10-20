# الفهرس المرتب — vx-agents-fabric

تاريخ الجرد: 2026-10-21 (الرياض).

- المستودع: `fisallllll280-code/vx-agents-fabric`.
- مصدر الجرد: شجرة Git الكاملة للالتزام `f0b3374a4245a8d128afc4bf05303c27b59c23fb`؛ دون اقتطاع.
- المسؤولية: تنسيق الوكلاء المتخصصين وعقود الأدوات والمراجعة.
- عدد الملفات قبل إضافة هذا الفهرس: **26**.
- الأصل: Derived / فهرس ملاحي مشتق من مسارات Git؛ لا يعيد ترقيم هويات Ω أو الفهرس التاريخي.
- الحالة: جرد ملفات مرصودة فقط؛ لا يثبت اجتياز الاختبارات أو التشغيل أو اعتماد المحتوى.

## 1. ترتيب القراءة والعمل

1. هوية المستودع وREADME وعقد المسؤولية إن وجد.
2. الفهارس والمواصفات والعقود والسياسات.
3. الشيفرة والموصلات والواجهات الموجودة.
4. الاختبارات وملفات CI والأدلة المسجلة؛ وجودها لا يثبت نجاحها.
5. التشغيل والاستعادة ثم مراجعة الأدلة والاعتماد.

## 2. حدود المسؤوليات بين المستودعات

| المستودع | المسؤولية | فهرسه في فرع المراجعة |
|---|---|---|
| VAIXLNS | المرجع المركزي للمعمارية والحوكمة والفهارس والاستعادة | [الفهرس](https://github.com/fisallllll280-code/VAIXLNS/blob/docs/ordered-repository-indexes-20261021/docs/indexes/ORDERED_REPOSITORY_INDEX_AR.md) |
| VAIXLNS-unified | التنفيذ المتكامل؛ لا يمنح سلطة اعتماد مرجعي | [الفهرس](https://github.com/fisallllll280-code/VAIXLNS-unified/blob/docs/ordered-repository-indexes-20261021/docs/indexes/ORDERED_REPOSITORY_INDEX_AR.md) |
| VX-runtime | التنفيذ المحكوم وسياسات القدرات والأحداث وإعادة التشغيل | [الفهرس](https://github.com/fisallllll280-code/VX-runtime/blob/docs/ordered-repository-indexes-20261021/docs/indexes/ORDERED_REPOSITORY_INDEX_AR.md) |
| NEXENT | البحث والاكتشاف والتركيب ومقترحات المعمارية | [الفهرس](https://github.com/fisallllll280-code/NEXENT/blob/docs/ordered-repository-indexes-20261021/docs/indexes/ORDERED_REPOSITORY_INDEX_AR.md) |
| NAXLNS | الهندسة وتحليل المستودعات ومرشحات التحقق | [الفهرس](https://github.com/fisallllll280-code/NAXLNS/blob/docs/ordered-repository-indexes-20261021/docs/indexes/ORDERED_REPOSITORY_INDEX_AR.md) |
| vx-financial-kernel | النواة المالية والمحاكاة؛ الوصف لا يثبت تشغيلًا ماليًا | [الفهرس](https://github.com/fisallllll280-code/vx-financial-kernel/blob/docs/ordered-repository-indexes-20261021/docs/indexes/ORDERED_REPOSITORY_INDEX_AR.md) |
| vx-agents-fabric | تنسيق الوكلاء المتخصصين وعقود الأدوات والمراجعة | [الفهرس](https://github.com/fisallllll280-code/vx-agents-fabric/blob/docs/ordered-repository-indexes-20261021/docs/indexes/ORDERED_REPOSITORY_INDEX_AR.md) |

VAIXLNS يحكم الاعتماد المرجعي. لا تثبت هذه الخريطة اتصالًا حيًا بين الأنظمة. تبقى مطابقة VLNS مع NAXLNS ومطابقة NEXNET مع NEXENT غير محسومتين وفق فهرس الاتحاد؛ لا إعادة تسمية أو دمج تلقائيًا.

## 3. ترتيب الفهارس الأصلي 00–27

الترتيب التالي من [تصنيف الفهرس الأصلي](https://github.com/fisallllll280-code/VAIXLNS/blob/6bd55a9b44696cc2c7746bc66e2d39f0f274a81f/registry/indexes/zero-loss-index-taxonomy.v1.json)؛ هو ترتيب مناظر الفهرس وليس أرقام بنود تاريخية.

| الترتيب | الفهرس | المفتاح الأصلي |
|---|---|---|
| 00 | المصادر | `source_index` |
| 01 | الفهرس التاريخي | `legacy_master_index` |
| 02 | الكيانات | `entity_index` |
| 03 | المصطلحات | `terminology_index` |
| 04 | الابتكارات | `innovation_index` |
| 05 | المعمارية | `architecture_index` |
| 06 | القدرات | `capability_index` |
| 07 | العقود | `contract_index` |
| 08 | الصلاحيات | `authority_index` |
| 09 | الأحداث | `event_index` |
| 10 | الحالات | `state_index` |
| 11 | الاعتماديات | `dependency_index` |
| 12 | العلاقات | `relation_index` |
| 13 | النسب والإصدارات التاريخية | `lineage_index` |
| 14 | المراجع المعتمدة | `canonical_index` |
| 15 | التنفيذ | `implementation_index` |
| 16 | المستودعات | `repository_index` |
| 17 | الملفات والمخرجات | `artifact_index` |
| 18 | الاختبارات | `test_index` |
| 19 | الأدلة | `evidence_index` |
| 20 | البراهين | `proof_index` |
| 21 | التشغيل | `operation_index` |
| 22 | الفشل والاستعادة | `failure_recovery_index` |
| 23 | الأمن | `security_index` |
| 24 | الرصد | `observability_index` |
| 25 | المحاكاة | `simulation_index` |
| 26 | التطور | `evolution_index` |
| 27 | الإحالات المتقاطعة | `cross_reference_index` |

## 4. جرد جميع الملفات بالترتيب

ترتيب ثابت بحسب المسار. الرقم هنا رقم عرض محلي فقط. البصمة **Git blob SHA-1** كما أعادتها واجهة Git وليست SHA-256 لبايتات الملف. روابط المصدر مثبتة على الالتزام أعلاه. لا يشمل الجرد فروعًا أخرى أو تاريخ Git الكامل أو ملفات خارج المستودع، ولا يشمل الفهرس الجديد نفسه.

| رقم العرض | الملف الأصلي | الحجم بالبايت | Git blob SHA-1 |
|---|---|---:|---|
| 0001 | [.github/workflows/tests.yml](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/.github/workflows/tests.yml) | 441 | `5d888d4cbacc2379c71f4f12bbc8063ff8c246f8` |
| 0002 | [README.md](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/README.md) | 7531 | `0c575fcb69534033dd65d5aac8973825e9d5d899` |
| 0003 | [docs/architecture.md](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/docs/architecture.md) | 9823 | `26d420110283d6b6d69b3628153d91d4adc3865a` |
| 0004 | [docs/engineering_tool_integrations.md](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/docs/engineering_tool_integrations.md) | 6887 | `428c97e215fcf482ccdfd9d9181fde8430cb627e` |
| 0005 | [docs/server_repository_inventory_v1.md](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/docs/server_repository_inventory_v1.md) | 14435 | `116f6ee17e215ec436208459e9d39f487d6811df` |
| 0006 | [pyproject.toml](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/pyproject.toml) | 337 | `fca29c4b32f82a524de87fa8586f6837b4b60664` |
| 0007 | [src/vx_agents_fabric/__init__.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/__init__.py) | 554 | `1068d84fcd37648efeccd2d05e77f802288b3fb7` |
| 0008 | [src/vx_agents_fabric/artifact_archive.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/artifact_archive.py) | 3953 | `9193639c2c51a361cbcdd31c5b38877672cb50a1` |
| 0009 | [src/vx_agents_fabric/cli.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/cli.py) | 6889 | `0e996dc4dfc37a5826bf10c4b3d6020d38878442` |
| 0010 | [src/vx_agents_fabric/closed_loop.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/closed_loop.py) | 12359 | `58b499472298a04326d723e725e63f2c3b154508` |
| 0011 | [src/vx_agents_fabric/contracts.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/contracts.py) | 4159 | `44d4a738c5797f4d06186f962077a1901f47d1ff` |
| 0012 | [src/vx_agents_fabric/engineering_tools.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/engineering_tools.py) | 35700 | `77b1fdba3ce7df17d7484c548851af5f1ea998f7` |
| 0013 | [src/vx_agents_fabric/failure_memory.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/failure_memory.py) | 5276 | `68ec6e0f1ac53c90ac928894ef8ae910f7cc2777` |
| 0014 | [src/vx_agents_fabric/ledger.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/ledger.py) | 4684 | `f234204fe3d46ac1157956f2a8e2fb7f76a03c03` |
| 0015 | [src/vx_agents_fabric/orchestrator.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/orchestrator.py) | 17874 | `4e40a9188fa9fb325ca2f0eb80633e093af21f7e` |
| 0016 | [src/vx_agents_fabric/providers/__init__.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/providers/__init__.py) | 220 | `1a838cd789a1cbe3cb8ff2de315614114fd7a19f` |
| 0017 | [src/vx_agents_fabric/providers/factory.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/providers/factory.py) | 3015 | `9d5953acd9a9397955758c3a04bc72db4e87870a` |
| 0018 | [src/vx_agents_fabric/providers/openai_compatible.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/providers/openai_compatible.py) | 9396 | `34113d69eed5fbc0e4ee91f61de3f2859da2071d` |
| 0019 | [src/vx_agents_fabric/registry.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/registry.py) | 14490 | `6c7e90ef362b2dd60cd82ad828d9c7811eedc29b` |
| 0020 | [src/vx_agents_fabric/tool_control.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/src/vx_agents_fabric/tool_control.py) | 10813 | `df96a29280e441811df53fb2f08417ff6205f7b7` |
| 0021 | [tests/test_cli.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/tests/test_cli.py) | 2081 | `91f03d44fcc77bf9157def8e30a2691922b460be` |
| 0022 | [tests/test_closed_loop.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/tests/test_closed_loop.py) | 9013 | `1f3c66c10058292731291519d2669e683f1e530d` |
| 0023 | [tests/test_engineering_tools.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/tests/test_engineering_tools.py) | 19377 | `44b2b0221d919f442912b710cc61928ba2d39f92` |
| 0024 | [tests/test_fabric.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/tests/test_fabric.py) | 7585 | `547698b028173a9f1c240ccd289bf4e0c6e789f1` |
| 0025 | [tests/test_ops_persistence.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/tests/test_ops_persistence.py) | 4448 | `c8b86e0d8b1ae8520a7370f49c38a9c3c94062ea` |
| 0026 | [tests/test_provider_bindings.py](https://github.com/fisallllll280-code/vx-agents-fabric/blob/f0b3374a4245a8d128afc4bf05303c27b59c23fb/tests/test_provider_bindings.py) | 3679 | `1a14d132200e18b4f6ed869bf80ee8b6767a0585` |

## 5. تحديث الفهرس والاستعادة

1. اقرأ عقود المستودع وأي AGENTS.md قبل التعديل، وثبّت التزام المصدر.
2. اجلب شجرة Git كاملة مع recursive=1 وارفض نتيجة truncated=true.
3. أعد الجرد بالمسار مع حجم كل ملف وبصمة blob، واحفظ مصدر كل سجل.
4. قارن الإضافات والتغييرات والحذف بالمصدر السابق؛ لا تحذف سجلًا تاريخيًا بصمت.
5. حافظ على أرقام الابتكارات الأصلية، وافصل رقم عرض الملفات عن legacy_id وcanonical_id.
6. احفظ التحديث في فرع مراجعة؛ لا دمج إلى main، ولا تعديل project.genome أو Ω.000 ضمن هذه المهمة.

## 6. الفجوات وحدود الإثبات

- الاستعادة الكاملة لبنود 0001–2750 غير مثبتة؛ لا تُنشأ بنود افتراضية لسد الأرقام.
- RECOVERED وCANONICAL وPROPOSED وIMPLEMENTED وVERIFIED حالات منفصلة؛ الجرد لا يرقّي أيًّا منها.
- فحص هذه المهمة يثبت مطابقة المسارات والبصمات لشجرة المصدر فقط؛ لا اختبارات تشغيلية نُفذت ضمن إنشاء هذا الملف.
