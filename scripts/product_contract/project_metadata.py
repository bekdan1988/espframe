from __future__ import annotations

import re
from pathlib import Path

from product_contract.common import (
    ROOT,
    check_relative_path,
    read,
    rel,
    require_contains,
)
from product_config import web_manual_entities, web_static_entities


def check_project_metadata(product: dict, errors: list[str]) -> None:
    project = product["project"]
    for field in (
        "name",
        "site_description",
        "ai_description",
        "social_image",
        "social_image_alt",
        "usb_flashing_image",
        "usb_flashing_image_alt",
        "web_installer_required_api",
        "web_installer_computer_requirement",
        "usb_cable_requirement",
        "usb_cable_warning",
        "immich_api_key_mode",
        "immich_api_key_privacy_promise",
        "home_assistant_name",
        "home_assistant_url",
        "home_assistant_requirement",
        "home_assistant_integration_platform",
        "device_log_level_default",
        "device_debug_update_interval",
        "firmware_update_source",
        "firmware_beta_channel_label",
        "firmware_manual_check_behavior",
        "firmware_beta_check_requirement",
        "firmware_custom_manifest_requirement",
        "ota_update_platform",
        "ota_pre_update_action",
        "ota_pre_update_transition",
        "ota_pre_update_delay",
        "backup_filename_prefix",
        "backup_filename_date_format",
        "backup_import_write_behavior",
        "backup_partial_config_behavior",
        "backup_invalid_photo_id_behavior",
        "privacy_connection_model",
        "privacy_network_scope",
        "privacy_no_cloud_service",
        "privacy_no_extra_account",
        "privacy_no_uploads",
        "privacy_no_hosted_service",
        "favicon",
        "npm_package_name",
        "license_id",
        "license_name",
        "owner_name",
        "owner_url",
        "package_name",
        "repository_url",
        "github_default_branch",
        "release_url_base",
        "release_artifact_prefix",
        "release_build_output_dir",
        "release_publish_dir",
        "release_uploaded_verify_dir",
        "release_source_factory_binary",
        "release_source_ota_binary",
        "release_esphome_cache_dir",
        "release_esphome_cache_key_prefix",
        "release_version_pattern",
        "stable_release_version_pattern",
        "firmware_version_placeholder_line",
        "firmware_local_build_version",
        "release_changelog_fallback_category",
        "phase_1_status_note",
        "public_base_url",
        "support_url",
        "support_button_image_url",
        "node_package_cache",
        "node_install_command",
        "local_check_command",
        "docs_build_command",
        "esphome_docker_image",
        "esphome_config_mount",
        "github_docs_release_meta_step_id",
        "github_docs_release_tag_env",
        "github_docs_release_tag_output",
        "github_docs_prerelease_tag_env",
        "github_pages_deployment_step_id",
        "github_pages_url_output",
        "web_ui_logs_event_source",
        "web_ui_logs_event_name",
        "web_ui_logs_clear_label",
        "node_version",
        "github_actions_runner",
        "github_docs_workflow_run_success_conclusion",
        "github_release_notes_version_ref",
        "github_release_build_version_ref",
        "github_release_build_ref",
        "github_release_notes_output",
    ):
        if not str(project.get(field, "")).strip():
            errors.append(f"project.{field} is required")

    package_name = str(project.get("package_name", "")).strip()
    if package_name and not re.match(r"^[A-Za-z0-9_.-]+\.[A-Za-z0-9_.-]+$", package_name):
        errors.append("project.package_name must look like a reverse-DNS package name")

    release_url_base = str(project.get("release_url_base", "")).strip()
    phase_1_status_note = check_relative_path(project.get("phase_1_status_note"), "project.phase_1_status_note", errors)
    repository_url = str(project.get("repository_url", "")).strip().rstrip("/")
    default_branch = str(project.get("github_default_branch", "")).strip()
    if repository_url and not repository_url.startswith("https://github.com/"):
        errors.append("project.repository_url must be an https GitHub URL")
    if default_branch and not re.match(r"^[A-Za-z0-9._/-]+$", default_branch):
        errors.append("project.github_default_branch contains unsupported characters")
    if default_branch and str(project.get("manual_setup_package_ref", "")).strip() != default_branch:
        errors.append("project.manual_setup_package_ref must match project.github_default_branch")
    if default_branch and str(project.get("external_component_ref", "")).strip() != default_branch:
        errors.append("project.external_component_ref must match project.github_default_branch")
    if release_url_base and not release_url_base.startswith("https://"):
        errors.append("project.release_url_base must be an https URL")
    if release_url_base and not release_url_base.endswith("/"):
        errors.append("project.release_url_base must end with /")
    if repository_url and release_url_base and release_url_base != f"{repository_url}/releases/tag/":
        errors.append("project.release_url_base must be based on project.repository_url")
    if phase_1_status_note:
        phase_1_path = ROOT / phase_1_status_note
        if not phase_1_status_note.startswith("docs/") or phase_1_path.suffix != ".md":
            errors.append("project.phase_1_status_note must point at a docs markdown file")
        phase_1_text = read(phase_1_path, errors)
        for needle in (
            "Product-owned behavior",
            "Generated outputs",
            "Validation gates",
            "Phase 2 boundary",
            "npm run check:product",
            "npm run check:all",
        ):
            require_contains(phase_1_text, needle, phase_1_status_note, errors)
    release_actions = project.get("release_workflow_actions", {})
    if not isinstance(release_actions, dict) or not release_actions:
        errors.append("project.release_workflow_actions must be a non-empty object")
    else:
        for name, action in release_actions.items():
            if not isinstance(name, str) or not name.strip():
                errors.append("project.release_workflow_actions keys must be non-empty strings")
            if not isinstance(action, str) or not action.strip():
                errors.append(f"project.release_workflow_actions.{name} must be a non-empty string")
    workflow_permissions = project.get("github_workflow_permissions", {})
    expected_workflows = {"compile", "docs", "release"}
    github_cli_env = project.get("github_cli_env", {})
    expected_github_cli_env = {"GH_TOKEN", "GH_REPO"}
    if not isinstance(github_cli_env, dict) or not github_cli_env:
        errors.append("project.github_cli_env must be a non-empty object")
    else:
        configured_env = {str(name).strip() for name in github_cli_env}
        missing_env = sorted(expected_github_cli_env - configured_env)
        extra_env = sorted(configured_env - expected_github_cli_env)
        if missing_env:
            errors.append(f"project.github_cli_env is missing variables: {', '.join(missing_env)}")
        if extra_env:
            errors.append(f"project.github_cli_env contains unknown variables: {', '.join(extra_env)}")
        for raw_name, raw_value in github_cli_env.items():
            name = str(raw_name).strip()
            value = str(raw_value).strip()
            if not name:
                errors.append("project.github_cli_env keys must be non-empty strings")
            if not value:
                errors.append(f"project.github_cli_env.{name or '<missing>'} must be a non-empty string")
    if not isinstance(workflow_permissions, dict) or not workflow_permissions:
        errors.append("project.github_workflow_permissions must be a non-empty object")
    else:
        configured_workflows = {str(name).strip() for name in workflow_permissions}
        missing_workflows = sorted(expected_workflows - configured_workflows)
        extra_workflows = sorted(configured_workflows - expected_workflows)
        if missing_workflows:
            errors.append(f"project.github_workflow_permissions is missing workflows: {', '.join(missing_workflows)}")
        if extra_workflows:
            errors.append(f"project.github_workflow_permissions contains unknown workflows: {', '.join(extra_workflows)}")
        for raw_name, permissions in workflow_permissions.items():
            name = str(raw_name).strip()
            if not name:
                errors.append("project.github_workflow_permissions keys must be non-empty strings")
            if not isinstance(permissions, dict) or not permissions:
                errors.append(f"project.github_workflow_permissions.{name or '<missing>'} must be a non-empty object")
                continue
            for raw_scope, raw_access in permissions.items():
                scope = str(raw_scope).strip()
                access = str(raw_access).strip()
                if not scope:
                    errors.append(f"project.github_workflow_permissions.{name or '<missing>'} scopes must be non-empty strings")
                if access not in {"read", "write", "none"}:
                    errors.append(
                        f"project.github_workflow_permissions.{name or '<missing>'}.{scope or '<missing>'} must be read, write, or none"
                    )
    workflow_names = project.get("github_workflow_names", {})
    if not isinstance(workflow_names, dict) or not workflow_names:
        errors.append("project.github_workflow_names must be a non-empty object")
    else:
        configured_workflows = {str(name).strip() for name in workflow_names}
        missing_workflows = sorted(expected_workflows - configured_workflows)
        extra_workflows = sorted(configured_workflows - expected_workflows)
        if missing_workflows:
            errors.append(f"project.github_workflow_names is missing workflows: {', '.join(missing_workflows)}")
        if extra_workflows:
            errors.append(f"project.github_workflow_names contains unknown workflows: {', '.join(extra_workflows)}")
        for raw_name, raw_label in workflow_names.items():
            name = str(raw_name).strip()
            label = str(raw_label).strip()
            if not name:
                errors.append("project.github_workflow_names keys must be non-empty strings")
            if not label:
                errors.append(f"project.github_workflow_names.{name or '<missing>'} must be a non-empty string")
    workflow_path_filters = project.get("github_workflow_path_filters", {})
    expected_path_filter_sets = {"compile_pull_request", "docs_push"}
    if not isinstance(workflow_path_filters, dict) or not workflow_path_filters:
        errors.append("project.github_workflow_path_filters must be a non-empty object")
    else:
        configured_filter_sets = {str(name).strip() for name in workflow_path_filters}
        missing_filter_sets = sorted(expected_path_filter_sets - configured_filter_sets)
        extra_filter_sets = sorted(configured_filter_sets - expected_path_filter_sets)
        if missing_filter_sets:
            errors.append(f"project.github_workflow_path_filters is missing filters: {', '.join(missing_filter_sets)}")
        if extra_filter_sets:
            errors.append(f"project.github_workflow_path_filters contains unknown filters: {', '.join(extra_filter_sets)}")
        for raw_name, raw_paths in workflow_path_filters.items():
            name = str(raw_name).strip()
            if not name:
                errors.append("project.github_workflow_path_filters keys must be non-empty strings")
            if not isinstance(raw_paths, list) or not raw_paths:
                errors.append(f"project.github_workflow_path_filters.{name or '<missing>'} must be a non-empty list")
                continue
            paths = [str(path).strip() for path in raw_paths]
            if any(not path for path in paths):
                errors.append(f"project.github_workflow_path_filters.{name or '<missing>'} must only contain non-empty strings")
            if len(paths) != len(set(paths)):
                errors.append(f"project.github_workflow_path_filters.{name or '<missing>'} must not contain duplicate paths")
    workflow_events = project.get("github_workflow_events", {})
    if not isinstance(workflow_events, dict) or not workflow_events:
        errors.append("project.github_workflow_events must be a non-empty object")
    else:
        configured_workflows = {str(name).strip() for name in workflow_events}
        missing_workflows = sorted(expected_workflows - configured_workflows)
        extra_workflows = sorted(configured_workflows - expected_workflows)
        if missing_workflows:
            errors.append(f"project.github_workflow_events is missing workflows: {', '.join(missing_workflows)}")
        if extra_workflows:
            errors.append(f"project.github_workflow_events contains unknown workflows: {', '.join(extra_workflows)}")
        for raw_name, raw_events in workflow_events.items():
            name = str(raw_name).strip()
            if not name:
                errors.append("project.github_workflow_events keys must be non-empty strings")
            if not isinstance(raw_events, list) or not raw_events:
                errors.append(f"project.github_workflow_events.{name or '<missing>'} must be a non-empty list")
                continue
            events = [str(event).strip() for event in raw_events]
            if any(not event for event in events):
                errors.append(f"project.github_workflow_events.{name or '<missing>'} must only contain non-empty strings")
            if len(events) != len(set(events)):
                errors.append(f"project.github_workflow_events.{name or '<missing>'} must not contain duplicate events")
    workflow_event_types = project.get("github_workflow_event_types", {})
    if not isinstance(workflow_event_types, dict) or not workflow_event_types:
        errors.append("project.github_workflow_event_types must be a non-empty object")
    else:
        for raw_key, raw_types in workflow_event_types.items():
            key = str(raw_key).strip()
            if "." not in key:
                errors.append(f"project.github_workflow_event_types.{key or '<missing>'} must use workflow.event format")
            if not isinstance(raw_types, list) or not raw_types:
                errors.append(f"project.github_workflow_event_types.{key or '<missing>'} must be a non-empty list")
                continue
            event_types = [str(event_type).strip() for event_type in raw_types]
            if any(not event_type for event_type in event_types):
                errors.append(f"project.github_workflow_event_types.{key or '<missing>'} must only contain non-empty strings")
            if len(event_types) != len(set(event_types)):
                errors.append(f"project.github_workflow_event_types.{key or '<missing>'} must not contain duplicate event types")
    workflow_jobs = project.get("github_workflow_jobs", {})
    if not isinstance(workflow_jobs, dict) or not workflow_jobs:
        errors.append("project.github_workflow_jobs must be a non-empty object")
    else:
        configured_workflows = {str(name).strip() for name in workflow_jobs}
        missing_workflows = sorted(expected_workflows - configured_workflows)
        extra_workflows = sorted(configured_workflows - expected_workflows)
        if missing_workflows:
            errors.append(f"project.github_workflow_jobs is missing workflows: {', '.join(missing_workflows)}")
        if extra_workflows:
            errors.append(f"project.github_workflow_jobs contains unknown workflows: {', '.join(extra_workflows)}")
        for raw_workflow, raw_jobs in workflow_jobs.items():
            workflow = str(raw_workflow).strip()
            if not workflow:
                errors.append("project.github_workflow_jobs keys must be non-empty strings")
            if not isinstance(raw_jobs, dict) or not raw_jobs:
                errors.append(f"project.github_workflow_jobs.{workflow or '<missing>'} must be a non-empty object")
                continue
            for raw_job_id, raw_job_name in raw_jobs.items():
                job_id = str(raw_job_id).strip()
                job_name = str(raw_job_name).strip()
                if not job_id:
                    errors.append(f"project.github_workflow_jobs.{workflow or '<missing>'} job ids must be non-empty strings")
                if not job_name:
                    errors.append(f"project.github_workflow_jobs.{workflow or '<missing>'}.{job_id or '<missing>'} must be a non-empty string")
    workflow_job_dependencies = project.get("github_workflow_job_dependencies", {})
    if not isinstance(workflow_job_dependencies, dict) or not workflow_job_dependencies:
        errors.append("project.github_workflow_job_dependencies must be a non-empty object")
    else:
        for raw_key, raw_dependencies in workflow_job_dependencies.items():
            key = str(raw_key).strip()
            workflow, _, job_id = key.partition(".")
            if not workflow or not job_id:
                errors.append(f"project.github_workflow_job_dependencies.{key or '<missing>'} must use workflow.job format")
            if not isinstance(raw_dependencies, list) or not raw_dependencies:
                errors.append(f"project.github_workflow_job_dependencies.{key or '<missing>'} must be a non-empty list")
                continue
            dependencies = [str(dependency).strip() for dependency in raw_dependencies]
            if any(not dependency for dependency in dependencies):
                errors.append(f"project.github_workflow_job_dependencies.{key or '<missing>'} must only contain non-empty strings")
            if len(dependencies) != len(set(dependencies)):
                errors.append(f"project.github_workflow_job_dependencies.{key or '<missing>'} must not contain duplicate jobs")
    sparse_checkout_files = project.get("github_sparse_checkout_files", [])
    if not isinstance(sparse_checkout_files, list) or not sparse_checkout_files:
        errors.append("project.github_sparse_checkout_files must be a non-empty list")
    else:
        paths = [str(path).strip() for path in sparse_checkout_files]
        if any(not path for path in paths):
            errors.append("project.github_sparse_checkout_files must only contain non-empty strings")
        if len(paths) != len(set(paths)):
            errors.append("project.github_sparse_checkout_files must not contain duplicate paths")
        for raw_path in paths:
            path = check_relative_path(raw_path, "project.github_sparse_checkout_files entry", errors)
            if path:
                read(ROOT / path, errors)
    if not isinstance(project.get("github_sparse_checkout_cone_mode"), bool):
        errors.append("project.github_sparse_checkout_cone_mode must be true or false")
    release_notes_fetch_depth = project.get("github_release_notes_fetch_depth")
    if not isinstance(release_notes_fetch_depth, int) or isinstance(release_notes_fetch_depth, bool) or release_notes_fetch_depth < 0:
        errors.append("project.github_release_notes_fetch_depth must be a non-negative integer")
    if not isinstance(project.get("github_release_notes_fetch_tags"), bool):
        errors.append("project.github_release_notes_fetch_tags must be true or false")
    if not isinstance(project.get("github_release_build_fail_fast"), bool):
        errors.append("project.github_release_build_fail_fast must be true or false")
    if not isinstance(project.get("esphome_docker_remove_container"), bool):
        errors.append("project.esphome_docker_remove_container must be true or false")
    release_asset_suffixes = project.get("release_asset_suffixes", [])
    if not isinstance(release_asset_suffixes, list) or not release_asset_suffixes:
        errors.append("project.release_asset_suffixes must be a non-empty list")
    elif any(not isinstance(suffix, str) or not suffix.strip() or not suffix.startswith(".") for suffix in release_asset_suffixes):
        errors.append("project.release_asset_suffixes must only contain non-empty dot-prefixed strings")
    for field in ("release_binary_download_patterns", "release_manifest_download_patterns", "release_uploaded_verify_patterns"):
        patterns = project.get(field, [])
        if not isinstance(patterns, list) or not patterns:
            errors.append(f"project.{field} must be a non-empty list")
        else:
            values = [str(pattern).strip() for pattern in patterns]
            if any(not value for value in values):
                errors.append(f"project.{field} must only contain non-empty strings")
            if len(values) != len(set(values)):
                errors.append(f"project.{field} must not contain duplicate patterns")
    cache_hash_files = project.get("release_esphome_cache_hash_files", [])
    if not isinstance(cache_hash_files, list) or not cache_hash_files:
        errors.append("project.release_esphome_cache_hash_files must be a non-empty list")
    else:
        values = [str(path).strip() for path in cache_hash_files]
        if any(not value for value in values):
            errors.append("project.release_esphome_cache_hash_files must only contain non-empty strings")
        if len(values) != len(set(values)):
            errors.append("project.release_esphome_cache_hash_files must not contain duplicate paths")
    for field in ("release_version_pattern", "stable_release_version_pattern"):
        pattern = str(project.get(field, "")).strip()
        if pattern:
            try:
                re.compile(pattern)
            except re.error as exc:
                errors.append(f"project.{field} must be a valid regular expression: {exc}")
    placeholder_versions = project.get("firmware_placeholder_versions", [])
    local_build_version = str(project.get("firmware_local_build_version", "")).strip()
    if not isinstance(placeholder_versions, list) or not placeholder_versions:
        errors.append("project.firmware_placeholder_versions must be a non-empty list")
    elif any(not isinstance(value, str) or not value.strip() for value in placeholder_versions):
        errors.append("project.firmware_placeholder_versions must only contain non-empty strings")
    elif "0.0.0" not in placeholder_versions:
        errors.append("project.firmware_placeholder_versions must include 0.0.0")
    elif default_branch and default_branch not in placeholder_versions:
        errors.append("project.firmware_placeholder_versions must include project.github_default_branch")
    elif local_build_version and local_build_version not in placeholder_versions:
        errors.append("project.firmware_placeholder_versions must include project.firmware_local_build_version")
    changelog_categories = project.get("release_changelog_categories", [])
    if not isinstance(changelog_categories, list) or not changelog_categories:
        errors.append("project.release_changelog_categories must be a non-empty list")
    else:
        seen_category_titles: set[str] = set()
        for category in changelog_categories:
            if not isinstance(category, dict):
                errors.append("project.release_changelog_categories entries must be objects")
                continue
            title = str(category.get("title", "")).strip()
            if not title:
                errors.append("project.release_changelog_categories entry is missing title")
            elif title in seen_category_titles:
                errors.append(f"Duplicate release changelog category: {title}")
            seen_category_titles.add(title)
            for field in ("paths", "keywords"):
                values = category.get(field, [])
                if not isinstance(values, list) or not values:
                    errors.append(f"project.release_changelog_categories.{title or '<missing>'}.{field} must be a non-empty list")
                elif any(not isinstance(value, str) or not value.strip() for value in values):
                    errors.append(f"project.release_changelog_categories.{title or '<missing>'}.{field} must only contain non-empty strings")
    for field in (
        "generated_asset_outputs",
        "generated_asset_sources",
        "web_template_placeholders",
        "web_initial_fetch_first_keys",
        "web_live_render_state_keys",
        "web_live_render_state_prefixes",
        "web_local_state_keys",
        "web_manual_state_keys",
    ):
        values = project.get(field, [])
        if not isinstance(values, list) or not values:
            errors.append(f"project.{field} must be a non-empty list")
        elif any(not isinstance(value, str) or not value.strip() for value in values):
            errors.append(f"project.{field} must only contain non-empty strings")
        elif len(values) != len(set(values)):
            errors.append(f"project.{field} must not contain duplicate entries")

    for field in ("support_url", "support_button_image_url"):
        value = str(project.get(field, "")).strip()
        if value and not value.startswith("https://"):
            errors.append(f"project.{field} must be an https URL")
    home_assistant_url = str(project.get("home_assistant_url", "")).strip()
    if home_assistant_url and not home_assistant_url.startswith("https://"):
        errors.append("project.home_assistant_url must be an https URL")
    owner_url = str(project.get("owner_url", "")).strip()
    if owner_url and not owner_url.startswith("https://"):
        errors.append("project.owner_url must be an https URL")
    for field in ("social_image", "usb_flashing_image", "favicon"):
        value = str(project.get(field, "")).strip()
        if value and (value.startswith("/") or ".." in Path(value).parts):
            errors.append(f"project.{field} must be a relative public asset path")
        if value:
            public_asset = ROOT / "docs" / "public" / value
            if not public_asset.is_file():
                errors.append(f"Missing file: {rel(public_asset)}")
    for field in (
        "web_installer_required_browsers",
        "web_installer_unsupported_browsers",
        "immich_server_url_schemes",
        "immich_server_url_targets",
        "immich_server_url_examples",
        "firmware_update_methods",
        "firmware_update_channels",
    ):
        values = project.get(field, [])
        if not isinstance(values, list) or not values:
            errors.append(f"project.{field} must be a non-empty list")
        elif any(not isinstance(value, str) or not value.strip() for value in values):
            errors.append(f"project.{field} must only contain non-empty strings")
    frequency_hours = project.get("firmware_update_frequency_hours", {})
    manifest_url_length_limit = project.get("firmware_manifest_url_length_limit")
    if not isinstance(manifest_url_length_limit, int) or isinstance(manifest_url_length_limit, bool) or manifest_url_length_limit < 1:
        errors.append("project.firmware_manifest_url_length_limit must be a positive integer")
    if not isinstance(frequency_hours, dict) or not frequency_hours:
        errors.append("project.firmware_update_frequency_hours must be a non-empty object")
    else:
        for label, hours in frequency_hours.items():
            if not isinstance(label, str) or not label.strip():
                errors.append("project.firmware_update_frequency_hours keys must be non-empty strings")
            if not isinstance(hours, int) or isinstance(hours, bool) or hours < 1:
                errors.append(f"project.firmware_update_frequency_hours.{label} must be a positive integer")
    home_assistant_features = project.get("home_assistant_integration_features", [])
    if not isinstance(home_assistant_features, list) or not home_assistant_features:
        errors.append("project.home_assistant_integration_features must be a non-empty list")
    elif any(not isinstance(value, str) or not value.strip() for value in home_assistant_features):
        errors.append("project.home_assistant_integration_features must only contain non-empty strings")
    network_entities = project.get("home_assistant_network_entities", [])
    if not isinstance(network_entities, list) or not network_entities:
        errors.append("project.home_assistant_network_entities must be a non-empty list")
    else:
        for entity in network_entities:
            if not isinstance(entity, dict):
                errors.append("project.home_assistant_network_entities entries must be objects")
                continue
            for field in ("name", "type", "description"):
                if not str(entity.get(field, "")).strip():
                    errors.append(f"project.home_assistant_network_entities entry is missing {field}")
    diagnostic_entities = project.get("home_assistant_diagnostic_entities", [])
    if not isinstance(diagnostic_entities, list) or not diagnostic_entities:
        errors.append("project.home_assistant_diagnostic_entities must be a non-empty list")
    else:
        for entity in diagnostic_entities:
            if not isinstance(entity, dict):
                errors.append("project.home_assistant_diagnostic_entities entries must be objects")
                continue
            for field in ("name", "type", "description"):
                if not str(entity.get(field, "")).strip():
                    errors.append(f"project.home_assistant_diagnostic_entities entry is missing {field}")
    component_log_levels = project.get("device_log_component_levels", {})
    if not isinstance(component_log_levels, dict) or not component_log_levels:
        errors.append("project.device_log_component_levels must be a non-empty object")
    else:
        for component, level in component_log_levels.items():
            if not isinstance(component, str) or not component.strip():
                errors.append("project.device_log_component_levels keys must be non-empty strings")
            if not isinstance(level, str) or not level.strip():
                errors.append(f"project.device_log_component_levels.{component} must be a non-empty string")
    for field in ("network_wifi_strength_source", "network_wifi_strength_update_interval"):
        if not str(project.get(field, "")).strip():
            errors.append(f"project.{field} is required")
    backup_config_version = project.get("backup_config_version")
    if not isinstance(backup_config_version, int) or isinstance(backup_config_version, bool) or backup_config_version < 1:
        errors.append("project.backup_config_version must be a positive integer")
    backup_import_photo_id_limit = project.get("backup_import_photo_id_limit")
    if (
        not isinstance(backup_import_photo_id_limit, int)
        or isinstance(backup_import_photo_id_limit, bool)
        or backup_import_photo_id_limit < 1
    ):
        errors.append("project.backup_import_photo_id_limit must be a positive integer")
    backup_excluded_values = project.get("backup_excluded_runtime_values", [])
    if not isinstance(backup_excluded_values, list) or not backup_excluded_values:
        errors.append("project.backup_excluded_runtime_values must be a non-empty list")
    elif any(not isinstance(value, str) or not value.strip() for value in backup_excluded_values):
        errors.append("project.backup_excluded_runtime_values must only contain non-empty strings")
    elif len({str(value).strip() for value in backup_excluded_values}) != len(backup_excluded_values):
        errors.append("project.backup_excluded_runtime_values must not contain duplicate values")
    backup_export_groups = project.get("backup_export_groups", [])
    if not isinstance(backup_export_groups, list) or not backup_export_groups:
        errors.append("project.backup_export_groups must be a non-empty list")
    elif any(not isinstance(value, str) or not value.strip() for value in backup_export_groups):
        errors.append("project.backup_export_groups must only contain non-empty strings")
    elif len({str(value).strip() for value in backup_export_groups}) != len(backup_export_groups):
        errors.append("project.backup_export_groups must not contain duplicate groups")
    backup_export_fields = project.get("backup_export_fields", {})
    if not isinstance(backup_export_fields, dict) or not backup_export_fields:
        errors.append("project.backup_export_fields must be a non-empty object")
    else:
        expected_groups = {str(group).strip() for group in backup_export_groups if str(group).strip()}
        configured_groups = {str(group).strip() for group in backup_export_fields}
        missing_groups = sorted(expected_groups - configured_groups)
        extra_groups = sorted(configured_groups - expected_groups)
        if missing_groups:
            errors.append(f"project.backup_export_fields is missing groups: {', '.join(missing_groups)}")
        if extra_groups:
            errors.append(f"project.backup_export_fields contains unknown groups: {', '.join(extra_groups)}")

        all_fields: set[str] = set()
        field_count = 0
        for raw_group, raw_fields in backup_export_fields.items():
            group = str(raw_group).strip()
            if not group:
                errors.append("project.backup_export_fields keys must be non-empty strings")
            if not isinstance(raw_fields, list) or not raw_fields:
                errors.append(f"project.backup_export_fields.{group or '<missing>'} must be a non-empty list")
                continue
            fields = [str(field).strip() for field in raw_fields]
            if any(not field for field in fields):
                errors.append(f"project.backup_export_fields.{group or '<missing>'} must only contain non-empty strings")
            if len(fields) != len(set(fields)):
                errors.append(f"project.backup_export_fields.{group or '<missing>'} must not contain duplicate fields")
            all_fields.update(fields)
            field_count += len(fields)
        if len(all_fields) != field_count:
            errors.append("project.backup_export_fields field names must be unique across groups")
    backup_state_mappings = project.get("backup_field_state_keys", {})
    if not isinstance(backup_state_mappings, dict) or not backup_state_mappings:
        errors.append("project.backup_field_state_keys must be a non-empty object")
    else:
        expected_group_fields = {
            (str(group).strip(), str(field).strip())
            for group, fields in project.get("backup_export_fields", {}).items()
            if isinstance(fields, list)
            for field in fields
            if str(group).strip() and str(field).strip()
        }
        configured_group_fields: set[tuple[str, str]] = set()
        valid_state_keys = (
            {str(setting.get("key", "")).strip() for setting in product.get("settings", [])}
            | set(web_static_entities(product))
            | set(web_manual_entities(product))
        )
        for raw_group, raw_fields in backup_state_mappings.items():
            group = str(raw_group).strip()
            if not group:
                errors.append("project.backup_field_state_keys keys must be non-empty strings")
                continue
            if not isinstance(raw_fields, dict) or not raw_fields:
                errors.append(f"project.backup_field_state_keys.{group} must be a non-empty object")
                continue
            for raw_field, raw_state_keys in raw_fields.items():
                field = str(raw_field).strip()
                if not field:
                    errors.append(f"project.backup_field_state_keys.{group} field keys must be non-empty strings")
                    continue
                configured_group_fields.add((group, field))
                if isinstance(raw_state_keys, list):
                    state_keys = [str(value).strip() for value in raw_state_keys]
                    if not state_keys:
                        errors.append(f"project.backup_field_state_keys.{group}.{field} must list at least one state key")
                    elif any(not value for value in state_keys):
                        errors.append(f"project.backup_field_state_keys.{group}.{field} must only contain non-empty strings")
                    elif len(state_keys) != len(set(state_keys)):
                        errors.append(f"project.backup_field_state_keys.{group}.{field} must not contain duplicate state keys")
                else:
                    state_key = str(raw_state_keys).strip()
                    state_keys = [state_key] if state_key else []
                    if not state_key:
                        errors.append(f"project.backup_field_state_keys.{group}.{field} must be a non-empty string or list")
                for state_key in state_keys:
                    if state_key not in valid_state_keys:
                        errors.append(f"Backup field {group}.{field} maps to unknown state key {state_key}")
        missing_mappings = sorted(expected_group_fields - configured_group_fields)
        extra_mappings = sorted(configured_group_fields - expected_group_fields)
        if missing_mappings:
            errors.append(
                "project.backup_field_state_keys is missing fields: "
                + ", ".join(f"{group}.{field}" for group, field in missing_mappings)
            )
        if extra_mappings:
            errors.append(
                "project.backup_field_state_keys contains unknown fields: "
                + ", ".join(f"{group}.{field}" for group, field in extra_mappings)
            )
    backup_fixture_files = project.get("backup_fixture_files", [])
    if not isinstance(backup_fixture_files, list) or not backup_fixture_files:
        errors.append("project.backup_fixture_files must be a non-empty list")
    elif len({str(fixture_file).strip() for fixture_file in backup_fixture_files}) != len(backup_fixture_files):
        errors.append("project.backup_fixture_files must not contain duplicate files")
    else:
        for fixture_file in backup_fixture_files:
            path = check_relative_path(fixture_file, "project.backup_fixture_files entry", errors)
            if path:
                read(ROOT / path, errors)
    compatibility_fixture_files = project.get("compatibility_fixture_files", {})
    if not isinstance(compatibility_fixture_files, dict) or not compatibility_fixture_files:
        errors.append("project.compatibility_fixture_files must be a non-empty object")
    else:
        accepted = compatibility_fixture_files.get("accepted", [])
        rejected_fields = compatibility_fixture_files.get("rejected_fields", [])
        if not isinstance(accepted, list) or not accepted:
            errors.append("project.compatibility_fixture_files.accepted must be a non-empty list")
        else:
            for fixture_file in accepted:
                path = check_relative_path(fixture_file, "project.compatibility_fixture_files.accepted entry", errors)
                if path:
                    read(ROOT / path, errors)
        if not isinstance(rejected_fields, list) or not rejected_fields:
            errors.append("project.compatibility_fixture_files.rejected_fields must be a non-empty list")
        else:
            for item in rejected_fields:
                if not isinstance(item, dict):
                    errors.append("project.compatibility_fixture_files.rejected_fields entries must be objects")
                    continue
                path = check_relative_path(item.get("path"), "project.compatibility_fixture_files.rejected_fields path", errors)
                if path:
                    read(ROOT / path, errors)
                messages = item.get("messages", [])
                if not isinstance(messages, list) or not messages:
                    errors.append(f"project.compatibility_fixture_files.rejected_fields {path or '<missing>'} messages must be a non-empty list")
                elif any(not isinstance(message, str) or not message.strip() for message in messages):
                    errors.append(f"project.compatibility_fixture_files.rejected_fields {path or '<missing>'} messages must be non-empty strings")
    touch_controls = project.get("touch_controls", [])
    if not isinstance(touch_controls, list) or not touch_controls:
        errors.append("project.touch_controls must be a non-empty list")
    else:
        for control in touch_controls:
            if not isinstance(control, dict):
                errors.append("project.touch_controls entries must be objects")
                continue
            if not str(control.get("action", "")).strip():
                errors.append("project.touch_controls entry is missing action")
            if not str(control.get("gesture", "")).strip():
                errors.append("project.touch_controls entry is missing gesture")
    for field in ("screen_brightness_day_night_source", "screen_schedule_behavior"):
        if not str(project.get(field, "")).strip():
            errors.append(f"project.{field} is required")
    for field in (
        "screen_rotation_feature_source",
        "screen_rotation_behavior",
        "screen_rotation_developer_behavior",
        "developer_features_query_value",
        "developer_features_label",
        "developer_features_entity",
        "developer_features_guard",
        "developer_features_persistence",
    ):
        if not str(project.get(field, "")).strip():
            errors.append(f"project.{field} is required")
    for field in ("screen_rotation_user_options", "screen_rotation_developer_options"):
        values = project.get(field, [])
        if not isinstance(values, list) or not values:
            errors.append(f"project.{field} must be a non-empty list")
        elif any(not isinstance(value, str) or not value.strip() for value in values):
            errors.append(f"project.{field} must only contain non-empty strings")
    developer_query_params = project.get("developer_features_query_params", [])
    if not isinstance(developer_query_params, list) or not developer_query_params:
        errors.append("project.developer_features_query_params must be a non-empty list")
    elif any(not isinstance(value, str) or not value.strip() for value in developer_query_params):
        errors.append("project.developer_features_query_params must only contain non-empty strings")
    screen_rotation_mapping = project.get("screen_rotation_native_mapping", {})
    if not isinstance(screen_rotation_mapping, dict) or not screen_rotation_mapping:
        errors.append("project.screen_rotation_native_mapping must be a non-empty object")
    else:
        for user_option, native_option in screen_rotation_mapping.items():
            if not isinstance(user_option, str) or not user_option.strip():
                errors.append("project.screen_rotation_native_mapping keys must be non-empty strings")
            if not isinstance(native_option, str) or not native_option.strip():
                errors.append(f"project.screen_rotation_native_mapping.{user_option} must be a non-empty string")
    for field in (
        "screen_tone_base_purpose",
        "screen_tone_night_timing",
        "screen_tone_night_recovery",
        "screen_tone_override_duration",
        "clock_default_format",
        "clock_default_timezone",
        "clock_update_interval",
    ):
        if not str(project.get(field, "")).strip():
            errors.append(f"project.{field} is required")
    clock_format_options = project.get("clock_format_options", [])
    if not isinstance(clock_format_options, list) or not clock_format_options:
        errors.append("project.clock_format_options must be a non-empty list")
    elif any(not isinstance(value, str) or not value.strip() for value in clock_format_options):
        errors.append("project.clock_format_options must only contain non-empty strings")
    if not isinstance(project.get("clock_default_show"), bool):
        errors.append("project.clock_default_show must be true or false")
    ntp_default_servers = project.get("ntp_default_servers", [])
    if not isinstance(ntp_default_servers, list) or not ntp_default_servers:
        errors.append("project.ntp_default_servers must be a non-empty list")
    elif any(not isinstance(value, str) or not value.strip() for value in ntp_default_servers):
        errors.append("project.ntp_default_servers must only contain non-empty strings")
    ntp_server_length_limit = project.get("ntp_server_length_limit")
    if not isinstance(ntp_server_length_limit, int) or isinstance(ntp_server_length_limit, bool) or ntp_server_length_limit < 1:
        errors.append("project.ntp_server_length_limit must be a positive integer")
    timezone_effects = project.get("timezone_change_effects", [])
    if not isinstance(timezone_effects, list) or not timezone_effects:
        errors.append("project.timezone_change_effects must be a non-empty list")
    elif any(not isinstance(value, str) or not value.strip() for value in timezone_effects):
        errors.append("project.timezone_change_effects must only contain non-empty strings")
    photo_source_modes = project.get("photo_source_modes", [])
    if not isinstance(photo_source_modes, list) or not photo_source_modes:
        errors.append("project.photo_source_modes must be a non-empty list")
    elif any(not isinstance(value, str) or not value.strip() for value in photo_source_modes):
        errors.append("project.photo_source_modes must only contain non-empty strings")
    for field in (
        "photo_source_auto_apply_behavior",
        "photo_source_memories_window",
        "photo_source_memories_fallback",
        "photo_source_album_person_sampling",
    ):
        if not str(project.get(field, "")).strip():
            errors.append(f"project.{field} is required")
    if not isinstance(project.get("photo_source_id_limit"), int) or isinstance(project.get("photo_source_id_limit"), bool):
        errors.append("project.photo_source_id_limit must be an integer")
    for field in (
        "connection_timeout_default",
        "connection_timeout_range",
        "connection_failure_trigger",
        "connection_invalid_api_key_title",
        "connection_unavailable_title",
    ):
        if not str(project.get(field, "")).strip():
            errors.append(f"project.{field} is required")
    if not isinstance(project.get("immich_max_error_retries"), int) or isinstance(project.get("immich_max_error_retries"), bool):
        errors.append("project.immich_max_error_retries must be an integer")
    retry_delays = project.get("immich_api_retry_delay_ms", [])
    if not isinstance(retry_delays, list) or not retry_delays:
        errors.append("project.immich_api_retry_delay_ms must be a non-empty list")
    elif any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in retry_delays):
        errors.append("project.immich_api_retry_delay_ms must only contain positive integers")
    retryable_statuses = project.get("immich_retryable_http_statuses", [])
    if not isinstance(retryable_statuses, list) or not retryable_statuses:
        errors.append("project.immich_retryable_http_statuses must be a non-empty list")
    elif any(not isinstance(value, str) or not value.strip() for value in retryable_statuses):
        errors.append("project.immich_retryable_http_statuses must only contain non-empty strings")
    if not isinstance(project.get("immich_auth_error_status"), int) or isinstance(project.get("immich_auth_error_status"), bool):
        errors.append("project.immich_auth_error_status must be an integer")
    for field in (
        "slideshow_interval_default_seconds",
        "connection_timeout_default_seconds",
        "docs_firmware_verify_retries",
        "docs_firmware_verify_delay_seconds",
        "firmware_compile_timeout_minutes",
    ):
        if not isinstance(project.get(field), int) or isinstance(project.get(field), bool) or project.get(field) < 1:
            errors.append(f"project.{field} must be a positive integer")
    for field in ("slideshow_interval_range_seconds", "connection_timeout_range_seconds"):
        value = project.get(field)
        if (
            not isinstance(value, list)
            or len(value) != 2
            or any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in value)
        ):
            errors.append(f"project.{field} must be a two-item list of positive integers")
        elif value[0] > value[1]:
            errors.append(f"project.{field} minimum must not exceed maximum")
    for field in (
        "slideshow_check_interval",
        "docs_dist_artifact_name",
        "docs_firmware_artifact_name",
        "docs_dist_output_path",
        "docs_deploy_path",
        "github_pages_environment",
        "github_pages_concurrency_group",
        "setup_captive_portal_ip",
        "setup_screen_dim_delay",
        "setup_screen_dim_brightness",
        "setup_screen_dim_transition",
        "setup_loading_backlight_brightness",
        "setup_loading_backlight_transition",
        "setup_connection_ready_condition",
        "manual_setup_package_ref",
        "manual_setup_package_refresh",
        "factory_firmware_purpose",
        "factory_firmware_secret_policy",
        "factory_firmware_network_mode",
        "factory_firmware_setup_method",
        "factory_firmware_local_use",
        "web_server_public_app_path",
        "web_server_factory_css_include",
        "web_server_factory_js_include",
        "external_component_git_source_type",
        "external_component_local_source_type",
        "external_component_git_path",
        "external_component_local_path",
        "external_component_ref",
    ):
        if not str(project.get(field, "")).strip():
            errors.append(f"project.{field} is required")
    for field in ("web_server_port", "web_server_version"):
        value = project.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            errors.append(f"project.{field} must be a positive integer")
    if not isinstance(project.get("web_server_include_internal"), bool):
        errors.append("project.web_server_include_internal must be true or false")
    if not isinstance(project.get("github_pages_cancel_in_progress"), bool):
        errors.append("project.github_pages_cancel_in_progress must be true or false")
    prerelease_lookup_limit = project.get("github_prerelease_lookup_limit")
    if not isinstance(prerelease_lookup_limit, int) or isinstance(prerelease_lookup_limit, bool) or prerelease_lookup_limit < 1:
        errors.append("project.github_prerelease_lookup_limit must be a positive integer")
    for field in ("github_release_download_clobber", "github_release_upload_clobber"):
        if not isinstance(project.get(field), bool):
            errors.append(f"project.{field} must be true or false")
    if "web_server_factory_js_url" not in project or not isinstance(project.get("web_server_factory_js_url"), str):
        errors.append("project.web_server_factory_js_url must be a string")
    sorting_groups = project.get("web_server_sorting_groups", [])
    if not isinstance(sorting_groups, list) or not sorting_groups:
        errors.append("project.web_server_sorting_groups must be a non-empty list")
    else:
        group_ids: set[str] = set()
        for group in sorting_groups:
            if not isinstance(group, dict):
                errors.append("project.web_server_sorting_groups entries must be objects")
                continue
            group_id = str(group.get("id", "")).strip()
            name = str(group.get("name", "")).strip()
            weight = group.get("sorting_weight")
            if not group_id:
                errors.append("project.web_server_sorting_groups entry is missing id")
            elif group_id in group_ids:
                errors.append(f"Duplicate project.web_server_sorting_groups id: {group_id}")
            group_ids.add(group_id)
            if not name:
                errors.append(f"project.web_server_sorting_groups.{group_id or '<missing>'} is missing name")
            if not isinstance(weight, int) or isinstance(weight, bool):
                errors.append(f"project.web_server_sorting_groups.{group_id or '<missing>'}.sorting_weight must be an integer")
    external_components = project.get("external_component_names", [])
    if not isinstance(external_components, list) or not external_components:
        errors.append("project.external_component_names must be a non-empty list")
    elif any(not isinstance(value, str) or not value.strip() for value in external_components):
        errors.append("project.external_component_names must only contain non-empty strings")
    for field in ("setup_wizard_steps", "setup_required_connection_fields", "setup_skip_substitutions"):
        values = project.get(field, [])
        if not isinstance(values, list) or not values:
            errors.append(f"project.{field} must be a non-empty list")
        elif any(not isinstance(value, str) or not value.strip() for value in values):
            errors.append(f"project.{field} must only contain non-empty strings")
    for field in ("manual_setup_required_substitutions", "manual_setup_wifi_secrets"):
        values = project.get(field, [])
        if not isinstance(values, list) or not values:
            errors.append(f"project.{field} must be a non-empty list")
        elif any(not isinstance(value, str) or not value.strip() for value in values):
            errors.append(f"project.{field} must only contain non-empty strings")
    web_ui_tabs = project.get("web_ui_tabs", [])
    if not isinstance(web_ui_tabs, list) or not web_ui_tabs:
        errors.append("project.web_ui_tabs must be a non-empty list")
    else:
        tab_ids: set[str] = set()
        for tab in web_ui_tabs:
            if not isinstance(tab, dict):
                errors.append("project.web_ui_tabs entries must be objects")
                continue
            tab_id = str(tab.get("id", "")).strip()
            tab_label = str(tab.get("label", "")).strip()
            if not tab_id:
                errors.append("project.web_ui_tabs entry is missing id")
            elif tab_id in tab_ids:
                errors.append(f"Duplicate project.web_ui_tabs id: {tab_id}")
            tab_ids.add(tab_id)
            if not tab_label:
                errors.append("project.web_ui_tabs entry is missing label")
    retained_log_lines = project.get("web_ui_logs_retained_lines")
    if not isinstance(retained_log_lines, int) or isinstance(retained_log_lines, bool) or retained_log_lines < 1:
        errors.append("project.web_ui_logs_retained_lines must be a positive integer")
    logs_event_source = str(project.get("web_ui_logs_event_source", "")).strip()
    logs_event_name = str(project.get("web_ui_logs_event_name", "")).strip()
    logs_clear_label = str(project.get("web_ui_logs_clear_label", "")).strip()
    if logs_event_source and (not logs_event_source.startswith("/") or any(char.isspace() for char in logs_event_source)):
        errors.append("project.web_ui_logs_event_source must be a root-relative path without whitespace")
    if logs_event_name and not re.match(r"^[A-Za-z][A-Za-z0-9_-]*$", logs_event_name):
        errors.append("project.web_ui_logs_event_name must be a non-empty event name")
    if logs_clear_label and len(logs_clear_label) > 40:
        errors.append("project.web_ui_logs_clear_label must be 40 characters or fewer")
    for field in ("date_filter_modes", "metadata_overlay_fields"):
        values = project.get(field, [])
        if not isinstance(values, list) or not values:
            errors.append(f"project.{field} must be a non-empty list")
        elif any(not isinstance(value, str) or not value.strip() for value in values):
            errors.append(f"project.{field} must only contain non-empty strings")
    for field in (
        "date_filter_relative_anchor",
        "date_filter_time_source",
        "portrait_pairing_behavior",
        "portrait_pairing_rotation_behavior",
    ):
        if not str(project.get(field, "")).strip():
            errors.append(f"project.{field} is required")
    screen_schedule_effects = project.get("screen_schedule_off_effects", [])
    if not isinstance(screen_schedule_effects, list) or not screen_schedule_effects:
        errors.append("project.screen_schedule_off_effects must be a non-empty list")
    elif any(not isinstance(value, str) or not value.strip() for value in screen_schedule_effects):
        errors.append("project.screen_schedule_off_effects must only contain non-empty strings")
    permissions = project.get("immich_api_key_permissions", [])
    if not isinstance(permissions, list) or not permissions:
        errors.append("project.immich_api_key_permissions must be a non-empty list")
    else:
        seen_permissions: set[str] = set()
        for permission in permissions:
            if not isinstance(permission, dict):
                errors.append("project.immich_api_key_permissions entries must be objects")
                continue
            name = str(permission.get("name", "")).strip()
            purpose = str(permission.get("purpose", "")).strip()
            if not name:
                errors.append("project.immich_api_key_permissions entry is missing name")
            elif name in seen_permissions:
                errors.append(f"Duplicate Immich API key permission: {name}")
            elif not re.match(r"^[a-z]+\.(read|view)$", name):
                errors.append(f"Immich API key permission should be read/view-only: {name}")
            seen_permissions.add(name)
            if not purpose:
                errors.append(f"Immich API key permission {name or '<missing>'} is missing purpose")

    firmware_update = read(ROOT / "common" / "addon" / "firmware_update.yaml", errors)
    if package_name:
        require_contains(firmware_update, f"name: {package_name}", "common/addon/firmware_update.yaml", errors)
