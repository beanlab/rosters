{{ read_file('general-instructions.md') }}

{% if project_info_path %}
# Project Context

{{ read_file(project_info_path) }}
{% endif %}
