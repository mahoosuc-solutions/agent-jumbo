import { z } from 'zod'
import { validatedApi } from '../client'

const FileStructureSettingsSchema = z.object({
  enabled: z.boolean(),
  max_depth: z.number(),
  max_files: z.number(),
  max_folders: z.number(),
  max_lines: z.number(),
  gitignore: z.string(),
}).passthrough()

export const ProjectSummarySchema = z.object({
  name: z.string(),
  title: z.string(),
  description: z.string(),
  color: z.string(),
}).passthrough()

export const ProjectDetailSchema = z.object({
  name: z.string(),
  title: z.string(),
  description: z.string(),
  instructions: z.string(),
  color: z.string(),
  memory: z.enum(['own', 'global']),
  file_structure: FileStructureSettingsSchema,
  instruction_files_count: z.number(),
  knowledge_files_count: z.number(),
  variables: z.string(),
  secrets: z.string(),
}).passthrough()

export type ProjectSummary = z.infer<typeof ProjectSummarySchema>
export type ProjectDetail = z.infer<typeof ProjectDetailSchema>

const ProjectsListResponseSchema = z.object({
  ok: z.boolean(),
  data: z.array(ProjectSummarySchema),
}).passthrough()

const ProjectDetailResponseSchema = z.object({
  ok: z.boolean(),
  data: ProjectDetailSchema,
}).passthrough()

const ProjectFileStructureResponseSchema = z.object({
  ok: z.boolean(),
  data: z.string(),
}).passthrough()

const ProjectActivateResponseSchema = z.object({
  ok: z.boolean(),
}).passthrough()

export function getProjects() {
  return validatedApi('projects', ProjectsListResponseSchema, {
    body: { action: 'list' },
  })
}

export function getProject(name: string) {
  return validatedApi('projects', ProjectDetailResponseSchema, {
    body: { action: 'load', name },
  })
}

export function getProjectFileStructure(name: string) {
  return validatedApi('projects', ProjectFileStructureResponseSchema, {
    body: { action: 'file_structure', name },
  })
}

export function activateProject(contextId: string, name: string) {
  return validatedApi('projects', ProjectActivateResponseSchema, {
    body: { action: 'activate', context_id: contextId, name },
  })
}
