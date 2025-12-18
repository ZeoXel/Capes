'use client'

import { useState } from 'react'
import {
  Search,
  Plus,
  MoreHorizontal,
  Trash2,
  Edit,
  Power,
  PowerOff,
  TestTube,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ArrowUpDown,
  Loader2,
} from 'lucide-react'
import { Heading } from '@/components/catalyst/heading'
import { Text } from '@/components/catalyst/text'
import { Badge } from '@/components/catalyst/badge'
import { Button } from '@/components/catalyst/button'
import { Input } from '@/components/catalyst/input'
import { Textarea } from '@/components/catalyst/textarea'
import {
  Dialog,
  DialogActions,
  DialogBody,
  DialogDescription,
  DialogTitle,
} from '@/components/catalyst/dialog'
import {
  Dropdown,
  DropdownButton,
  DropdownMenu,
  DropdownItem,
  DropdownLabel,
  DropdownDivider,
} from '@/components/catalyst/dropdown'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/catalyst/table'
import { Field, Label, Description, Fieldset } from '@/components/catalyst/fieldset'
import { Select } from '@/components/catalyst/select'
import { Switch, SwitchField } from '@/components/catalyst/switch'

// Mock data
const channels = [
  {
    id: '1',
    name: 'OpenAI 官方',
    type: 'openai',
    baseUrl: 'https://api.openai.com/v1',
    status: 'active',
    priority: 1,
    weight: 100,
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    usedQuota: 125000,
    balance: 500.00,
    responseTime: 320,
    successRate: 99.8,
    lastTest: '2 分钟前',
  },
  {
    id: '2',
    name: 'Azure OpenAI',
    type: 'azure',
    baseUrl: 'https://xxx.openai.azure.com',
    status: 'active',
    priority: 2,
    weight: 80,
    models: ['gpt-4o', 'gpt-4-turbo'],
    usedQuota: 89000,
    balance: 1200.00,
    responseTime: 280,
    successRate: 99.5,
    lastTest: '5 分钟前',
  },
  {
    id: '3',
    name: 'Anthropic Claude',
    type: 'anthropic',
    baseUrl: 'https://api.anthropic.com/v1',
    status: 'active',
    priority: 1,
    weight: 100,
    models: ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'],
    usedQuota: 67000,
    balance: 300.00,
    responseTime: 450,
    successRate: 99.2,
    lastTest: '1 分钟前',
  },
  {
    id: '4',
    name: 'Google Gemini',
    type: 'google',
    baseUrl: 'https://generativelanguage.googleapis.com/v1',
    status: 'active',
    priority: 1,
    weight: 90,
    models: ['gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-1.5-pro'],
    usedQuota: 45000,
    balance: 200.00,
    responseTime: 380,
    successRate: 98.9,
    lastTest: '3 分钟前',
  },
  {
    id: '5',
    name: '第三方代理',
    type: 'proxy',
    baseUrl: 'https://api.bltcy.ai/v1',
    status: 'active',
    priority: 3,
    weight: 50,
    models: ['gpt-4o', 'claude-3-sonnet', 'gemini-2.5-flash'],
    usedQuota: 230000,
    balance: 150.00,
    responseTime: 520,
    successRate: 97.5,
    lastTest: '10 分钟前',
  },
  {
    id: '6',
    name: '备用渠道',
    type: 'openai',
    baseUrl: 'https://api.backup.com/v1',
    status: 'disabled',
    priority: 10,
    weight: 10,
    models: ['gpt-4o-mini'],
    usedQuota: 5000,
    balance: 50.00,
    responseTime: 0,
    successRate: 0,
    lastTest: '从未',
  },
]

type Channel = typeof channels[0]

const channelTypes = [
  { id: 'openai', name: 'OpenAI', color: 'green' },
  { id: 'azure', name: 'Azure OpenAI', color: 'blue' },
  { id: 'anthropic', name: 'Anthropic', color: 'orange' },
  { id: 'google', name: 'Google', color: 'red' },
  { id: 'proxy', name: '代理/中转', color: 'purple' },
  { id: 'custom', name: '自定义', color: 'zinc' },
]

const allModels = [
  'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo',
  'claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku',
  'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-1.5-pro',
]

function StatusIndicator({ status, successRate }: { status: string; successRate: number }) {
  if (status === 'disabled') {
    return (
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-zinc-300" />
        <span className="text-zinc-500">已禁用</span>
      </div>
    )
  }

  const color = successRate >= 99 ? 'green' : successRate >= 95 ? 'amber' : 'red'
  const Icon = successRate >= 99 ? CheckCircle2 : successRate >= 95 ? AlertCircle : XCircle

  return (
    <div className="flex items-center gap-2">
      <Icon className={`size-4 text-${color}-500`} />
      <span className={`text-${color}-600 font-medium`}>{successRate}%</span>
    </div>
  )
}

function ChannelRow({ channel, onEdit, onTest }: { channel: Channel; onEdit: (c: Channel) => void; onTest: (c: Channel) => void }) {
  const typeInfo = channelTypes.find(t => t.id === channel.type)

  return (
    <TableRow className={channel.status === 'disabled' ? 'opacity-50' : ''}>
      <TableCell>
        <div className="flex items-center gap-3">
          <div className={`w-2 h-8 rounded-full ${channel.status === 'active' ? 'bg-green-500' : 'bg-zinc-300'}`} />
          <div>
            <p className="font-medium text-zinc-900 dark:text-white">{channel.name}</p>
            <p className="text-sm text-zinc-500 font-mono">{channel.baseUrl}</p>
          </div>
        </div>
      </TableCell>
      <TableCell>
        <Badge color={typeInfo?.color as any || 'zinc'}>{typeInfo?.name || channel.type}</Badge>
      </TableCell>
      <TableCell>
        <div className="flex flex-wrap gap-1 max-w-48">
          {channel.models.slice(0, 3).map((model) => (
            <Badge key={model} color="zinc" className="text-xs">{model}</Badge>
          ))}
          {channel.models.length > 3 && (
            <Badge color="zinc" className="text-xs">+{channel.models.length - 3}</Badge>
          )}
        </div>
      </TableCell>
      <TableCell className="text-center">
        <div className="flex items-center justify-center gap-1">
          <span className="font-medium">{channel.priority}</span>
          <span className="text-zinc-400">/</span>
          <span className="text-zinc-500">{channel.weight}%</span>
        </div>
      </TableCell>
      <TableCell>
        <StatusIndicator status={channel.status} successRate={channel.successRate} />
      </TableCell>
      <TableCell className="text-right">
        <div>
          <p className="font-medium tabular-nums">{channel.responseTime > 0 ? `${channel.responseTime}ms` : '-'}</p>
          <p className="text-xs text-zinc-500">{channel.lastTest}</p>
        </div>
      </TableCell>
      <TableCell className="text-right tabular-nums">
        ${channel.balance.toFixed(2)}
      </TableCell>
      <TableCell>
        <Dropdown>
          <DropdownButton plain>
            <MoreHorizontal className="size-4" />
          </DropdownButton>
          <DropdownMenu anchor="bottom end">
            <DropdownItem onClick={() => onEdit(channel)}>
              <Edit data-slot="icon" className="size-4" />
              <DropdownLabel>编辑</DropdownLabel>
            </DropdownItem>
            <DropdownItem onClick={() => onTest(channel)}>
              <TestTube data-slot="icon" className="size-4" />
              <DropdownLabel>测试连接</DropdownLabel>
            </DropdownItem>
            <DropdownItem>
              <ArrowUpDown data-slot="icon" className="size-4" />
              <DropdownLabel>调整优先级</DropdownLabel>
            </DropdownItem>
            <DropdownDivider />
            {channel.status === 'active' ? (
              <DropdownItem>
                <PowerOff data-slot="icon" className="size-4" />
                <DropdownLabel>禁用</DropdownLabel>
              </DropdownItem>
            ) : (
              <DropdownItem>
                <Power data-slot="icon" className="size-4" />
                <DropdownLabel>启用</DropdownLabel>
              </DropdownItem>
            )}
            <DropdownItem className="text-red-600">
              <Trash2 data-slot="icon" className="size-4" />
              <DropdownLabel>删除</DropdownLabel>
            </DropdownItem>
          </DropdownMenu>
        </Dropdown>
      </TableCell>
    </TableRow>
  )
}

export default function ChannelsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [isTestOpen, setIsTestOpen] = useState(false)
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null)
  const [testResult, setTestResult] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [selectedModels, setSelectedModels] = useState<string[]>([])

  const filteredChannels = channels.filter((channel) => {
    const matchesSearch = channel.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      channel.baseUrl.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = typeFilter === 'all' || channel.type === typeFilter
    return matchesSearch && matchesType
  })

  const handleEdit = (channel: Channel) => {
    setSelectedChannel(channel)
    setSelectedModels(channel.models)
    setIsCreateOpen(true)
  }

  const handleTest = (channel: Channel) => {
    setSelectedChannel(channel)
    setTestResult('idle')
    setIsTestOpen(true)
  }

  const runTest = () => {
    setTestResult('testing')
    // 模拟测试
    setTimeout(() => {
      setTestResult(Math.random() > 0.2 ? 'success' : 'error')
    }, 2000)
  }

  const toggleModel = (model: string) => {
    setSelectedModels(prev =>
      prev.includes(model)
        ? prev.filter(m => m !== model)
        : [...prev, model]
    )
  }

  const activeChannels = channels.filter(c => c.status === 'active')
  const avgResponseTime = Math.round(
    activeChannels.reduce((acc, c) => acc + c.responseTime, 0) / activeChannels.length
  )
  const avgSuccessRate = (
    activeChannels.reduce((acc, c) => acc + c.successRate, 0) / activeChannels.length
  ).toFixed(1)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Heading>渠道管理</Heading>
          <Text className="mt-1 text-zinc-500">
            配置 API 渠道、负载均衡和故障转移
          </Text>
        </div>
        <Button onClick={() => { setSelectedChannel(null); setSelectedModels([]); setIsCreateOpen(true) }}>
          <Plus className="size-4" />
          添加渠道
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-4">
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Text className="text-zinc-500">总渠道</Text>
          <p className="text-2xl font-semibold mt-1">{channels.length}</p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Text className="text-zinc-500">活跃渠道</Text>
          <p className="text-2xl font-semibold mt-1 text-green-600">{activeChannels.length}</p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Text className="text-zinc-500">平均响应</Text>
          <p className="text-2xl font-semibold mt-1">{avgResponseTime}ms</p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Text className="text-zinc-500">成功率</Text>
          <p className="text-2xl font-semibold mt-1">{avgSuccessRate}%</p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Text className="text-zinc-500">总余额</Text>
          <p className="text-2xl font-semibold mt-1">
            ${channels.reduce((acc, c) => acc + c.balance, 0).toFixed(2)}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-zinc-400" />
          <Input
            type="text"
            placeholder="搜索渠道..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        >
          <option value="all">全部类型</option>
          {channelTypes.map(type => (
            <option key={type.id} value={type.id}>{type.name}</option>
          ))}
        </Select>
        <Button outline onClick={() => channels.forEach(c => c.status === 'active' && handleTest(c))}>
          <TestTube className="size-4" />
          全部测试
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900 overflow-hidden">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>渠道</TableHeader>
              <TableHeader>类型</TableHeader>
              <TableHeader>支持模型</TableHeader>
              <TableHeader className="text-center">优先级/权重</TableHeader>
              <TableHeader>状态</TableHeader>
              <TableHeader className="text-right">响应时间</TableHeader>
              <TableHeader className="text-right">余额</TableHeader>
              <TableHeader className="w-12"></TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredChannels.map((channel) => (
              <ChannelRow
                key={channel.id}
                channel={channel}
                onEdit={handleEdit}
                onTest={handleTest}
              />
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={isCreateOpen} onClose={setIsCreateOpen}>
        <DialogTitle>{selectedChannel ? '编辑渠道' : '添加渠道'}</DialogTitle>
        <DialogDescription>
          {selectedChannel ? '修改渠道配置' : '配置新的 API 渠道'}
        </DialogDescription>
        <DialogBody className="space-y-6">
          <Fieldset>
            <Field>
              <Label>渠道名称</Label>
              <Input
                type="text"
                placeholder="例如：OpenAI 官方"
                defaultValue={selectedChannel?.name}
              />
            </Field>

            <Field>
              <Label>渠道类型</Label>
              <Select defaultValue={selectedChannel?.type || 'openai'}>
                {channelTypes.map(type => (
                  <option key={type.id} value={type.id}>{type.name}</option>
                ))}
              </Select>
            </Field>

            <Field>
              <Label>Base URL</Label>
              <Input
                type="url"
                placeholder="https://api.openai.com/v1"
                defaultValue={selectedChannel?.baseUrl}
              />
              <Description>API 端点地址，不含路径</Description>
            </Field>

            <Field>
              <Label>API Key</Label>
              <Input
                type="password"
                placeholder="sk-..."
              />
              <Description>留空表示不修改</Description>
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field>
                <Label>优先级</Label>
                <Input
                  type="number"
                  min="1"
                  max="100"
                  defaultValue={selectedChannel?.priority || 1}
                />
                <Description>数字越小优先级越高</Description>
              </Field>
              <Field>
                <Label>权重</Label>
                <Input
                  type="number"
                  min="1"
                  max="100"
                  defaultValue={selectedChannel?.weight || 100}
                />
                <Description>同优先级下的分配权重</Description>
              </Field>
            </div>

            <Field>
              <Label>支持模型</Label>
              <div className="mt-2 flex flex-wrap gap-2">
                {allModels.map(model => (
                  <button
                    key={model}
                    type="button"
                    onClick={() => toggleModel(model)}
                    className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                      selectedModels.includes(model)
                        ? 'bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-300'
                        : 'border-zinc-200 text-zinc-600 hover:border-zinc-300 dark:border-zinc-700 dark:text-zinc-400'
                    }`}
                  >
                    {model}
                  </button>
                ))}
              </div>
              <Description>选择此渠道支持的模型</Description>
            </Field>

            <SwitchField>
              <Label>启用渠道</Label>
              <Description>启用后将参与请求分发</Description>
              <Switch defaultChecked={selectedChannel?.status !== 'disabled'} />
            </SwitchField>
          </Fieldset>
        </DialogBody>
        <DialogActions>
          <Button plain onClick={() => setIsCreateOpen(false)}>
            取消
          </Button>
          <Button onClick={() => setIsCreateOpen(false)}>
            {selectedChannel ? '保存' : '创建'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Test Dialog */}
      <Dialog open={isTestOpen} onClose={setIsTestOpen}>
        <DialogTitle>测试渠道连接</DialogTitle>
        <DialogDescription>
          测试 {selectedChannel?.name} 的连接状态
        </DialogDescription>
        <DialogBody>
          <div className="space-y-4">
            <div className="p-4 bg-zinc-50 dark:bg-zinc-800 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <Text className="font-medium">Base URL</Text>
                <Text className="font-mono text-sm">{selectedChannel?.baseUrl}</Text>
              </div>
              <div className="flex items-center justify-between">
                <Text className="font-medium">支持模型</Text>
                <Text>{selectedChannel?.models.length} 个</Text>
              </div>
            </div>

            {testResult === 'idle' && (
              <div className="text-center py-8">
                <TestTube className="size-12 mx-auto text-zinc-300 mb-4" />
                <Text>点击下方按钮开始测试</Text>
              </div>
            )}

            {testResult === 'testing' && (
              <div className="text-center py-8">
                <Loader2 className="size-12 mx-auto text-blue-500 animate-spin mb-4" />
                <Text>正在测试连接...</Text>
              </div>
            )}

            {testResult === 'success' && (
              <div className="text-center py-8">
                <CheckCircle2 className="size-12 mx-auto text-green-500 mb-4" />
                <Text className="text-green-600 font-medium">连接成功</Text>
                <Text className="text-sm text-zinc-500 mt-2">响应时间: 285ms</Text>
              </div>
            )}

            {testResult === 'error' && (
              <div className="text-center py-8">
                <XCircle className="size-12 mx-auto text-red-500 mb-4" />
                <Text className="text-red-600 font-medium">连接失败</Text>
                <Text className="text-sm text-zinc-500 mt-2">错误: API Key 无效或已过期</Text>
              </div>
            )}
          </div>
        </DialogBody>
        <DialogActions>
          <Button plain onClick={() => setIsTestOpen(false)}>
            关闭
          </Button>
          <Button onClick={runTest} disabled={testResult === 'testing'}>
            {testResult === 'testing' ? '测试中...' : '开始测试'}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  )
}
