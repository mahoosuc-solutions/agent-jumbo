import { z } from 'zod'
import { validatedApi } from '../client'
import { GmailAccountsResponseSchema } from '../schemas'

export interface GmailAccount {
  email: string
  authenticated: boolean
  scopes: string[]
  added_date: string
}

export interface GmailAccountsResponse {
  accounts: Record<string, GmailAccount>
}

export function listGmailAccounts(): Promise<GmailAccountsResponse> {
  return validatedApi('gmail_accounts_list', GmailAccountsResponseSchema) as Promise<GmailAccountsResponse>
}

const RemoveAccountResponseSchema = z.object({ success: z.boolean() }).passthrough()

export function removeGmailAccount(accountName: string): Promise<{ success: boolean }> {
  return validatedApi('gmail_account_remove', RemoveAccountResponseSchema, { body: { account_name: accountName } })
}

const OAuthStartResponseSchema = z.object({ auth_url: z.string() }).passthrough()

export function startGmailOAuth(accountName: string): Promise<{ auth_url: string }> {
  return validatedApi('gmail_oauth_start', OAuthStartResponseSchema, { body: { account_name: accountName } })
}
