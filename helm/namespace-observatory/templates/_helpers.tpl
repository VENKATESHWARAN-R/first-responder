{{/*
Common labels
*/}}
{{- define "nso.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels for backend
*/}}
{{- define "nso.backend.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}-backend
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Selector labels for frontend
*/}}
{{- define "nso.frontend.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}-frontend
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "nso.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (printf "%s" .Release.Name) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
