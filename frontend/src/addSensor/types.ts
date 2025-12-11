export interface FieldDefinition {
  name: string
  type: string
  required: boolean
  description: string
  default: any
  example: any
  values: string[] | null
}

export interface SensorTemplate {
  common_fields: FieldDefinition[]
  http_fields: FieldDefinition[]
  websocket_fields: FieldDefinition[]
  custom_fields: FieldDefinition[]
}

