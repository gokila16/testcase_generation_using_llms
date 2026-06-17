# Target System

This pipeline is a fork of **test_generator_v7** (the frozen PDFBox/Avro pipeline),
adapted to a new target system. The generate → compile → run → grade core is
unchanged; only `config.py`, step-1 metadata extraction, and the Maven module
target differ.

- **Target project:** Apache Wicket
- **Version (pinned):** 10.9.1  (`rel/wicket-10.9.1`, pom `wicket-parent` 10.9.1)
- **Source under test:** `wicket-core` module → `org.apache.wicket.*`
  - Path: `apache_wicket/wicket/wicket-core/src/main/java`
- **Test harness the generated tests must use:** `WicketTester` (and `FormTester`,
  `TagTester`) from the `wicket-tester` module (`org.apache.wicket.util.tester.*`).
  Wicket components cannot be `new`-ed and called directly; they need a simulated
  web request. The WicketTester setup is injected via the per-method `construction`
  field in `dependency_chains.json` (built by `build_dependency_chains.py`), so
  `prompt_builder.py` stays untouched.
- **Style reference:** `wicket-core-tests` module (real WicketTester tests).

## Provenance
Forked from `test_generator_v7/test_generator/` — code and docs only.
PDFBox data (metadata JSON, dependency_chains.json, class_inventory.json, CSVs)
and outputs were intentionally NOT copied; they are regenerated for Wicket by
step 1.

## Key structural finding (Wicket 10.9.1)
`wicket-core` holds the SOURCE under test but has almost no tests of its own
(2 files). The real unit tests (~1160 files) live in the separate
`wicket-core-tests` module, which depends on `wicket-tester` + `wicket-core`.
=> Generated tests must COMPILE & RUN in `wicket-core-tests`, not `wicket-core`.
config vars: source = `PDFBOX_DIR` (wicket-core); tests = `WICKET_TESTS_MODULE`
(wicket-core-tests). There is no classic src/test/resources (markup sits in
META-INF/resources next to classes).

## Status
- [x] Phase 0 — fork created (this folder), inside apache_wicket/
- [x] Phase 1 — config.py repointed to wicket-core / 10.9.1 (names kept for
      frozen-code compat; PDFBOX_DIR -> wicket-core; added WICKET_TESTS_MODULE)
- [x] Phase 2 — step-1 extraction done against wicket-core.
      * pipeline package copied into fork; pipeline/config.py -> wicket paths.
      * Understand DB (understand/wicket_core.und) over core+util+request+tester
        (1090 files, analyze: 0 errors). Build via the und create/add/analyze
        commands (und is on PATH). Run step1 with PYTHONIOENCODING=utf-8 to dodge
        a cp1252 print crash (Mac-authored '->' char) — no pipeline code edited.
      * Output: extracted_metadata.json (4438 OK public methods, all
        org.apache.wicket.*, 4293 with bodies) + extraction_summary.csv +
        public_methods.csv in the fork dir.
      * NOTE: 4438 = ALL public methods. Anonymous-inner-class entries
        (e.g. Anon_1.onInstantiation) and trivial getters/setters still present;
        filtering to the ~1256 non-trivial/testable set happens in Phase 3.
- [x] Phase 3 — enrichment + WicketTester recipes. Three artifacts built:
      * class_inventory.json (1345 classes). build_class_inventory.py repointed
        to wicket modules; added _desugar_for_javalang() shim to strip Java 16+
        `instanceof X x` pattern bindings (javalang 0.13 can't parse them — broke
        Form/FormComponent and the whole form-input inheritance chain).
      * dependency_chains.json (1423 methods). build_dependency_chains.py
        repointed; added a Wicket-aware resolve_receiver:
          - categorize class-under-test via inventory extends-chain
            (Page / Component / Behavior);
          - emit a FULLY-QUALIFIED WicketTester scaffold (no imports needed):
            page -> tester.startPage(...); component -> new C("id") +
            tester.startComponentInPage(...);
          - abstract/interface class-under-test -> substitute a concrete
            subclass with a (String id) ctor (e.g. FormComponent -> TextField).
          Result: 215 wicket_component + 9 wicket_page receivers, 0 abstract
          instantiations. Behaviors/POJOs fall through to the generic resolver.
      * extracted_metadata_final.json ENRICHED in place via enrich_*.py under
        upython (Understand): 1421/1423 have source_file_imports, 875 have
        dependency_signatures. Now has the full 15-field schema prompt_builder
        expects. (Backup: extracted_metadata_final.prennrich.bak)
      * Also dropped 90 Anon_* anonymous-inner-class entries (1513 -> 1423).
- [x] Phase 4 — generated tests compile & run in wicket-core-tests. NO
      maven_runner.py edits — pure config:
      * PDFBOX_DIR -> wicket-core-tests (maven_runner uses it as test-placement
        dir AND maven cwd). wicket-core does NOT depend on wicket-tester, so a
        WicketTester test only compiles in wicket-core-tests. This is how the
        wicket-tester-on-classpath requirement is met.
      * GENERATED_TESTS_DIR -> separate archive dir (was wrongly src/test/java,
        which would SameFileError the copy step).
      * wicket-tester API exposed to the LLM: WicketTester/FormTester/TagTester
        injected into source_file_imports of the 224 wicket-receiver methods
        (they're in class_inventory, so the prompt's AVAILABLE PROJECT CLASSES
        section now lists their methods). Data-only; no prompt_builder edit.
      * Prereq done: `mvn install -Dmaven.test.skip -Dmaven.javadoc.skip
        -pl wicket-tester -am` to put wicket 10.9.1 (parent/util/request/core/
        tester) in local .m2. JDK 25 builds Wicket fine; javadoc MUST be skipped
        (JDK 25 doclint rejects old {@link} tags in package.html).
      * Baseline: all ~1160 existing wicket-core-tests compile under JDK 25.
      * SMOKE: a WicketTester test (new Label("id","hello") +
        startComponentInPage) compiled + ran green via the exact maven_runner
        goals (Tests run: 1, Failures: 0). Path proven end-to-end.
      * PERF NOTE: maven_runner compiles ALL of src/test/java each run, so every
        generated test triggers a full recompile of ~1160 files (slow per
        iteration but correct). Revisit if Phase 5 is too slow.
- [ ] Phase 5 — smoke test the PIPELINE itself (~15-20 real methods across
      Page/Component/util) end to end: prompt -> LLM -> generate -> compile ->
      run -> grade. Needs OPENAI_API_KEY. Measures compile/pass rate; iterate on
      the wicket recipes only.
