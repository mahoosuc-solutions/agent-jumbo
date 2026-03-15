import { validatedApi } from '../client'
import { BackupListResponseSchema, CreateBackupResponseSchema, OkResponseSchema } from '../schemas'

export interface Backup {
  id: string
  name: string
  size: number
  created_at: string
}

export function listBackups(): Promise<{ backups: Backup[] }> {
  return validatedApi('backup_list', BackupListResponseSchema)
}

export function createBackup(): Promise<{ ok: boolean; id: string }> {
  return validatedApi('backup_create', CreateBackupResponseSchema)
}

export function restoreBackup(id: string): Promise<{ ok: boolean }> {
  return validatedApi('backup_restore', OkResponseSchema, { body: { id } })
}
