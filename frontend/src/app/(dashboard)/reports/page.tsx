import ReportCard from '@/components/reports/ReportCard'
import EmbeddedChat from '@/components/reports/EmbeddedChat'

const reports = [
  {
    slug: 'invitations',
    label: 'Invitation Status',
    description: 'Track pending, accepted, and expired employee invitations.',
    icon: '📨',
  },
  {
    slug: 'recognition',
    label: 'Recognition Activity',
    description: 'Overview of all recognition activity across the workspace.',
    icon: '🏆',
  },
  {
    slug: 'recognition/given',
    label: 'Recognition Given',
    description: 'See which employees are giving the most recognition.',
    icon: '🤝',
  },
  {
    slug: 'recognition/received',
    label: 'Recognition Received',
    description: 'See which employees are being recognized most often.',
    icon: '⭐',
  },
  {
    slug: 'seats',
    label: 'Active Seat Usage',
    description: 'Monitor purchased seats vs active users in real time.',
    icon: '💺',
  },
  {
    slug: 'redemptions',
    label: 'Voucher Redemption',
    description: 'Track employee voucher redemptions and spend by brand.',
    icon: '🎁',
  },
  {
    slug: 'wallet',
    label: 'Wallet Balance',
    description: 'Current wallet balance and low balance alerts.',
    icon: '💰',
  },
  {
    slug: 'wallet/transactions',
    label: 'Wallet Transactions',
    description: 'Full ledger of wallet recharges and deductions.',
    icon: '📒',
  },
  {
    slug: 'payments',
    label: 'Payment History',
    description: 'Subscription payment history, invoices, and status.',
    icon: '🧾',
  },
  {
    slug: 'onboarding',
    label: 'Employee Onboarding',
    description: 'CSV import history and employee activation funnel.',
    icon: '👋',
  },
  {
    slug: 'subscription',
    label: 'Subscription Billing',
    description: 'Current plan, seat count, and billing cycle details.',
    icon: '📋',
  },
  {
    slug: 'emails',
    label: 'Email Notifications',
    description: 'Delivery status and open rates for system emails.',
    icon: '📧',
  },
]

export default function ReportsPage() {
  return (
    <div>

      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">Reports</h1>
        <p className="mt-1 text-sm text-slate-500">
          Select a report to view data for your workspace.
        </p>
      </div>

      {/* Cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {reports.map((report) => (
          <ReportCard
            key={report.slug}
            slug={report.slug}
            label={report.label}
            description={report.description}
            icon={report.icon}
          />
        ))}
      </div>

      <EmbeddedChat />

      


    </div>
  )
}