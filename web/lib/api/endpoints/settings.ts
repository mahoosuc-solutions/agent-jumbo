import { z } from 'zod'
import { validatedApi } from '../client'
import { SettingsOutputSchema, SettingsSectionSchema } from '../schemas'

export interface FieldOption {
  value: string
  label: string
}

export interface SettingsField {
  id: string
  title: string
  description: string
  type: 'text' | 'number' | 'select' | 'range' | 'textarea' | 'password' | 'switch' | 'button' | 'html'
  value: unknown
  min?: number
  max?: number
  step?: number
  hidden?: boolean
  options?: FieldOption[]
  style?: string
}

export interface SettingsSection {
  id: string
  title: string
  description: string
  tab: string
  fields: SettingsField[]
}

export interface SettingsOutput {
  settings: { sections: SettingsSection[] }
}

export function getSettings(): Promise<SettingsOutput> {
  return validatedApi('settings_get', SettingsOutputSchema, { method: 'GET' })
}

const SaveSettingsResponseSchema = z.object({ settings: z.object({ sections: z.array(SettingsSectionSchema) }).passthrough() }).passthrough()

export function saveSettings(values: Record<string, unknown>): Promise<{ settings: { sections: SettingsSection[] } }> {
  return validatedApi('settings_set', SaveSettingsResponseSchema, { body: values })
}
