import {
  MessageSquare, LayoutDashboard, Rocket, Workflow, Calendar,
  MessageCircle, Puzzle, Eye, GitBranch, Brain, FolderOpen,
  Archive, Users, Settings, ClipboardList, Lightbulb, FolderKanban, BriefcaseBusiness, type LucideIcon,
} from 'lucide-react'

export const SITE_NAME = 'Agent Jumbo'
export const SITE_DESCRIPTION = 'Your Personal AI Operating System. Part of Mahoosuc OS.'
export const GITHUB_REPO = 'mahoosuc-solutions/agent-jumbo'
export const GITHUB_URL = 'https://github.com/mahoosuc-solutions/agent-jumbo'
export const MAHOOSUC_URL = 'https://mahoosuc.ai'
export const VERSION = '1.0.0-beta'

export const FEATURES = [
  {
    icon: '🚀',
    title: 'Deploy Anywhere',
    description: 'Kubernetes, AWS, GCP, SSH, GitHub Actions. One agent definition deploys everywhere with approval gates and automatic rollback.',
  },
  {
    icon: '🔐',
    title: 'Enterprise Governance',
    description: 'Approval workflows, HMAC audit logs, passkey authentication, and rate limiting. Compliance-ready from day one.',
  },
  {
    icon: '📊',
    title: 'Real-Time Visibility',
    description: 'Monitor costs, execution metrics, and agent behavior in real-time. Know exactly what\'s happening in production.',
  },
  {
    icon: '🔧',
    title: 'Integrate Everything',
    description: '100+ REST APIs, webhook support, OAuth2. Connect to Gmail, Slack, PMS platforms, and more seamlessly.',
  },
]

export const PUBLIC_NAVIGATION = [
  { label: 'Home', href: '/' },
  { label: 'How It Works', href: '/how-it-works' },
  { label: 'Install', href: '/install' },
  { label: 'Documentation', href: '/documentation' },
  { label: 'Mahoosuc OS ↗', href: 'https://mahoosuc.ai', external: true },
]

export interface NavItem {
  label: string
  href: string
  icon: LucideIcon
  badge?: string
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

export const APP_NAVIGATION: NavGroup[] = [
  {
    label: 'Core',
    items: [
      { label: 'Chat', href: '/chat', icon: MessageSquare },
      { label: 'Overview', href: '/overview', icon: LayoutDashboard },
      { label: 'Opportunities', href: '/opportunities', icon: BriefcaseBusiness },
      { label: 'Ideas', href: '/ideas', icon: Lightbulb },
      { label: 'Projects', href: '/projects', icon: FolderKanban },
    ],
  },
  {
    label: 'Operate',
    items: [
      { label: 'Deployments', href: '/deployments', icon: Rocket },
      { label: 'Workflows', href: '/workflows', icon: Workflow },
      { label: 'Work Queue', href: '/work-queue', icon: ClipboardList },
      { label: 'Scheduler', href: '/scheduler', icon: Calendar },
    ],
  },
  {
    label: 'Communicate',
    items: [
      { label: 'Messaging', href: '/messaging', icon: MessageCircle },
    ],
  },
  {
    label: 'Build',
    items: [
      { label: 'Skills', href: '/skills', icon: Puzzle },
      { label: 'Files', href: '/files', icon: FolderOpen },
      { label: 'Memory', href: '/memory', icon: Brain },
    ],
  },
  {
    label: 'Observe',
    items: [
      { label: 'Observability', href: '/observability', icon: Eye },
      { label: 'LLM Router', href: '/llm-router', icon: GitBranch },
    ],
  },
  {
    label: 'Manage',
    items: [
      { label: 'Backups', href: '/backups', icon: Archive },
      { label: 'Collaboration', href: '/collaboration', icon: Users },
      { label: 'Settings', href: '/settings', icon: Settings },
    ],
  },
]
