'use client'

import { useState } from 'react'
import {
  Users,
  Key,
  MessageSquare,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Activity,
  Zap,
} from 'lucide-react'
import { Heading, Subheading } from '@/components/catalyst/heading'
import { Text } from '@/components/catalyst/text'
import { Badge } from '@/components/catalyst/badge'
import { Button } from '@/components/catalyst/button'
import { Divider } from '@/components/catalyst/divider'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/catalyst/table'

// Mock data - 后续会从 API 获取
const stats = [
  {
    name: '总用户数',
    value: '2,847',
    change: '+12%',
    changeType: 'positive' as const,
    icon: Users,
  },
  {
    name: 'API 密钥',
    value: '156',
    change: '+8%',
    changeType: 'positive' as const,
    icon: Key,
  },
  {
    name: '今日调用',
    value: '45,231',
    change: '+23%',
    changeType: 'positive' as const,
    icon: MessageSquare,
  },
  {
    name: '今日消费',
    value: '$127.50',
    change: '-5%',
    changeType: 'negative' as const,
    icon: DollarSign,
  },
]

const recentActivity = [
  { id: 1, user: 'user@example.com', action: '调用 gpt-4o', tokens: 1250, cost: '$0.025', time: '2 分钟前' },
  { id: 2, user: 'dev@company.com', action: '调用 claude-3-sonnet', tokens: 3200, cost: '$0.048', time: '5 分钟前' },
  { id: 3, user: 'test@demo.com', action: '调用 gemini-2.5-flash', tokens: 890, cost: '$0.012', time: '8 分钟前' },
  { id: 4, user: 'user@example.com', action: '生成图像 DALL-E', tokens: 0, cost: '$0.040', time: '12 分钟前' },
  { id: 5, user: 'admin@site.com', action: '调用 gpt-4o', tokens: 2100, cost: '$0.042', time: '15 分钟前' },
]

const topModels = [
  { name: 'gpt-4o', calls: 12500, percentage: 35 },
  { name: 'claude-3-sonnet', calls: 8900, percentage: 25 },
  { name: 'gemini-2.5-flash', calls: 7200, percentage: 20 },
  { name: 'gpt-4o-mini', calls: 4500, percentage: 13 },
  { name: '其他', calls: 2500, percentage: 7 },
]

function StatCard({ stat }: { stat: typeof stats[0] }) {
  const Icon = stat.icon
  const isPositive = stat.changeType === 'positive'

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center justify-between">
        <div className="rounded-lg bg-zinc-100 p-2 dark:bg-zinc-800">
          <Icon className="size-5 text-zinc-600 dark:text-zinc-400" />
        </div>
        <Badge color={isPositive ? 'green' : 'red'} className="gap-1">
          {isPositive ? (
            <TrendingUp className="size-3" />
          ) : (
            <TrendingDown className="size-3" />
          )}
          {stat.change}
        </Badge>
      </div>
      <div className="mt-4">
        <Text className="text-zinc-500">{stat.name}</Text>
        <p className="text-2xl font-semibold text-zinc-900 dark:text-white mt-1">
          {stat.value}
        </p>
      </div>
    </div>
  )
}

function ModelUsageBar({ model }: { model: typeof topModels[0] }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-zinc-900 dark:text-white">{model.name}</span>
        <span className="text-zinc-500">{model.calls.toLocaleString()} 次</span>
      </div>
      <div className="h-2 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
        <div
          className="h-full rounded-full bg-blue-600 transition-all duration-500"
          style={{ width: `${model.percentage}%` }}
        />
      </div>
    </div>
  )
}

export default function AdminDashboard() {
  const [timeRange, setTimeRange] = useState<'today' | 'week' | 'month'>('today')

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Heading>控制台概览</Heading>
          <Text className="mt-1 text-zinc-500">
            查看系统运行状态和关键指标
          </Text>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-zinc-200 dark:border-zinc-700 p-1">
            {(['today', 'week', 'month'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  timeRange === range
                    ? 'bg-zinc-900 text-white dark:bg-white dark:text-zinc-900'
                    : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white'
                }`}
              >
                {range === 'today' ? '今日' : range === 'week' ? '本周' : '本月'}
              </button>
            ))}
          </div>
          <Button outline>
            <Activity className="size-4" />
            实时监控
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.name} stat={stat} />
        ))}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Recent Activity */}
        <div className="lg:col-span-2 rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
          <div className="p-6 pb-4">
            <div className="flex items-center justify-between">
              <Subheading>最近调用</Subheading>
              <Button plain href="/admin/logs">
                查看全部
              </Button>
            </div>
          </div>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeader>用户</TableHeader>
                <TableHeader>操作</TableHeader>
                <TableHeader className="text-right">Token</TableHeader>
                <TableHeader className="text-right">费用</TableHeader>
                <TableHeader className="text-right">时间</TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {recentActivity.map((activity) => (
                <TableRow key={activity.id}>
                  <TableCell className="font-medium">{activity.user}</TableCell>
                  <TableCell>
                    <Badge color="zinc">{activity.action}</Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {activity.tokens.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {activity.cost}
                  </TableCell>
                  <TableCell className="text-right text-zinc-500">
                    {activity.time}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Model Usage */}
        <div className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
          <div className="flex items-center justify-between mb-6">
            <Subheading>模型调用分布</Subheading>
            <Badge color="blue" className="gap-1">
              <Zap className="size-3" />
              实时
            </Badge>
          </div>
          <div className="space-y-5">
            {topModels.map((model) => (
              <ModelUsageBar key={model.name} model={model} />
            ))}
          </div>
          <Divider className="my-6" />
          <div className="flex items-center justify-between text-sm">
            <span className="text-zinc-500">总调用次数</span>
            <span className="font-semibold text-zinc-900 dark:text-white">
              {topModels.reduce((acc, m) => acc + m.calls, 0).toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
        <Subheading className="mb-4">快捷操作</Subheading>
        <div className="flex flex-wrap gap-3">
          <Button href="/admin/users">
            <Users className="size-4" />
            添加用户
          </Button>
          <Button href="/admin/keys" outline>
            <Key className="size-4" />
            生成密钥
          </Button>
          <Button href="/admin/channels" outline>
            添加渠道
          </Button>
          <Button href="/admin/pricing" outline>
            调整定价
          </Button>
        </div>
      </div>
    </div>
  )
}
