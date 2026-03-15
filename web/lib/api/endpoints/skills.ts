import { z } from 'zod'
import { validatedApi } from '../client'
import { SkillSchema, ScanResultSchema, OkResponseSchema } from '../schemas'

export type TrustLevel = 'builtin' | 'verified' | 'community' | 'local'
export type SkillTier = 'markdown' | 'python'

export interface Skill {
  name: string
  version: string
  author: string
  description: string
  category: string
  tier: SkillTier
  trust_level: TrustLevel
  enabled: boolean
  installed: boolean
  source: 'tool' | 'instrument'
  capabilities: string[]
}

export interface ScanResult {
  name: string
  safe: boolean
  issues: ScanIssue[]
  scanned_at: string
}

export interface ScanIssue {
  severity: 'low' | 'medium' | 'high' | 'critical'
  message: string
  file: string
  line: number
}

const SkillsListResponseSchema = z.object({ skills: z.array(SkillSchema) }).passthrough()

export function fetchSkills(): Promise<{ skills: Skill[] }> {
  return validatedApi('skills_list', SkillsListResponseSchema, { method: 'GET' })
}

export function fetchSkill(name: string): Promise<Skill> {
  return validatedApi('skills_get', SkillSchema, { method: 'GET', params: { name } })
}

export function installSkill(nameOrPath: string): Promise<{ ok: boolean }> {
  return validatedApi('skills_install', OkResponseSchema, { body: { name_or_path: nameOrPath } })
}

export function uninstallSkill(name: string): Promise<{ ok: boolean }> {
  return validatedApi('skills_uninstall', OkResponseSchema, { body: { name } })
}

export function toggleSkill(name: string, enabled: boolean): Promise<{ ok: boolean }> {
  return validatedApi('skills_toggle', OkResponseSchema, { body: { name, enabled } })
}

export function scanSkill(nameOrPath: string): Promise<ScanResult> {
  return validatedApi('skills_scan', ScanResultSchema, { body: { name_or_path: nameOrPath } })
}

const SkillsSearchResponseSchema = z.object({ results: z.array(SkillSchema) }).passthrough()

export function searchSkills(query: string): Promise<{ results: Skill[] }> {
  return validatedApi('skills_search', SkillsSearchResponseSchema, { method: 'GET', params: { query } })
}
