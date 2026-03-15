import { validatedApi } from '../client'
import { FileBrowserResultSchema, OkResponseSchema } from '../schemas'

export interface FileEntry {
  name: string
  path: string
  type: 'file' | 'directory'
  size?: number
  modified?: string
}

export interface FileBrowserResult {
  data: {
    files: FileEntry[]
    current_path: string
    parent_path: string | null
  }
}

export function getWorkDirFiles(path = ''): Promise<FileBrowserResult> {
  return validatedApi('get_work_dir_files', FileBrowserResultSchema, {
    method: 'GET',
    params: { path },
  })
}

export function deleteWorkDirFile(path: string): Promise<{ ok: boolean }> {
  return validatedApi('delete_work_dir_file', OkResponseSchema, { body: { path } })
}
