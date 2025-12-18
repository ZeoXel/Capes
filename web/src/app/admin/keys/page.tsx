'use client'

import { useState } from 'react'
import {
  Search,
  Plus,
  MoreHorizontal,
  Copy,
  Eye,
  EyeOff,
  Trash2,
  Edit,
  RefreshCw,
  CheckCircle2,
} from 'lucide-react'
import { Heading } from '@/components/catalyst/heading'
import { Text } from '@/components/catalyst/text'
import { Badge } from '@/components/catalyst/badge'
import { Button } from '@/components/catalyst/button'
import { Input } from '@/components/catalyst/input'
import { Checkbox, CheckboxField } from '@/components/catalyst/checkbox'
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

// Mock data
const apiKeys = [
  {
    id: '1',
    name: '生产环境 Key',
    key: 'sk-cape-prod-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    user: 'admin@example.com',
    status: 'active',
    models: ['all'],
    rateLimit: 100,
    usedTokens: 1250000,
    totalTokens: -1,
    createdAt: '2024-01-15',
    lastUsed: '刚刚',
    expiresAt: null,
  },
  {
    id: '2',
    name: '开发测试',
    key: 'sk-cape-dev-yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy',
    user: 'developer@company.com',
    status: 'active',
    models: ['gpt-4o', 'gpt-4o-mini', 'claude-3-sonnet'],
    rateLimit: 50,
    usedTokens: 89000,
    totalTokens: 500000,
    createdAt: '2024-02-20',
    lastUsed: '5 分钟前',
    expiresAt: '2025-02-20',
  },
  {
    id: '3',
    name: 'API 集成',
    key: 'sk-cape-api-zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz',
    user: 'test@demo.com',
    status: 'active',
    models: ['gemini-2.5-flash'],
    rateLimit: 20,
    usedTokens: 45000,
    totalTokens: 100000,
    createdAt: '2024-03-10',
    lastUsed: '1 小时前',
    expiresAt: '2024-12-31',
  },
  {
    id: '4',
    name: '已禁用 Key',
    key: 'sk-cape-old-wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww',
    user: 'suspended@user.com',
    status: 'disabled',
    models: ['gpt-4o'],
    rateLimit: 10,
    usedTokens: 10000,
    totalTokens: 10000,
    createdAt: '2024-01-20',
    lastUsed: '30 天前',
    expiresAt: null,
  },
]

type ApiKey = typeof apiKeys[0]

const availableModels = [
  { id: 'gpt-4o', name: 'GPT-4o' },
  { id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
  { id: 'claude-3-sonnet', name: 'Claude 3 Sonnet' },
  { id: 'claude-3-opus', name: 'Claude 3 Opus' },
  { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash' },
  { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro' },
]

function KeyDisplay({ keyValue, showFull }: { keyValue: string; showFull: boolean }) {
  const [copied, setCopied] = useState(false)

  const displayKey = showFull
    ? keyValue
    : keyValue.slice(0, 12) + '...' + keyValue.slice(-4)

  const handleCopy = () => {
    navigator.clipboard.writeText(keyValue)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex items-center gap-2">
      <code className="text-sm font-mono bg-zinc-100 dark:bg-zinc-800 px-2 py-1 rounded">
        {displayKey}
      </code>
      <button
        onClick={handleCopy}
        className="p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded"
        title="复制"
      >
        {copied ? (
          <CheckCircle2 className="size-4 text-green-500" />
        ) : (
          <Copy className="size-4 text-zinc-400" />
        )}
      </button>
    </div>
  )
}

function KeyRow({ apiKey, onEdit }: { apiKey: ApiKey; onEdit: (key: ApiKey) => void }) {
  const [showKey, setShowKey] = useState(false)
  const usagePercentage = apiKey.totalTokens === -1
    ? 0
    : (apiKey.usedTokens / apiKey.totalTokens) * 100

  return (
    <TableRow>
      <TableCell>
        <div>
          <p className="font-medium text-zinc-900 dark:text-white">{apiKey.name}</p>
          <p className="text-sm text-zinc-500">{apiKey.user}</p>
        </div>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <KeyDisplay keyValue={apiKey.key} showFull={showKey} />
          <button
            onClick={() => setShowKey(!showKey)}
            className="p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded"
            title={showKey ? '隐藏' : '显示'}
          >
            {showKey ? (
              <EyeOff className="size-4 text-zinc-400" />
            ) : (
              <Eye className="size-4 text-zinc-400" />
            )}
          </button>
        </div>
      </TableCell>
      <TableCell>
        <Badge color={apiKey.status === 'active' ? 'green' : 'red'}>
          {apiKey.status === 'active' ? '启用' : '禁用'}
        </Badge>
      </TableCell>
      <TableCell>
        <div className="flex flex-wrap gap-1">
          {apiKey.models[0] === 'all' ? (
            <Badge color="blue">全部模型</Badge>
          ) : (
            apiKey.models.slice(0, 2).map((model) => (
              <Badge key={model} color="zinc">{model}</Badge>
            ))
          )}
          {apiKey.models.length > 2 && (
            <Badge color="zinc">+{apiKey.models.length - 2}</Badge>
          )}
        </div>
      </TableCell>
      <TableCell>
        <div className="space-y-1 min-w-32">
          <div className="flex items-center justify-between text-sm">
            <span className="text-zinc-500">
              {apiKey.usedTokens.toLocaleString()}
            </span>
            <span className="text-zinc-400">
              / {apiKey.totalTokens === -1 ? '无限' : apiKey.totalTokens.toLocaleString()}
            </span>
          </div>
          {apiKey.totalTokens !== -1 && (
            <div className="h-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  usagePercentage > 90 ? 'bg-red-500' :
                  usagePercentage > 80 ? 'bg-amber-500' : 'bg-blue-500'
                }`}
                style={{ width: `${Math.min(usagePercentage, 100)}%` }}
              />
            </div>
          )}
        </div>
      </TableCell>
      <TableCell className="text-zinc-500">{apiKey.lastUsed}</TableCell>
      <TableCell>
        <Dropdown>
          <DropdownButton plain>
            <MoreHorizontal className="size-4" />
          </DropdownButton>
          <DropdownMenu anchor="bottom end">
            <DropdownItem onClick={() => onEdit(apiKey)}>
              <Edit data-slot="icon" className="size-4" />
              <DropdownLabel>编辑</DropdownLabel>
            </DropdownItem>
            <DropdownItem>
              <RefreshCw data-slot="icon" className="size-4" />
              <DropdownLabel>重新生成</DropdownLabel>
            </DropdownItem>
            <DropdownDivider />
            {apiKey.status === 'active' ? (
              <DropdownItem>
                <EyeOff data-slot="icon" className="size-4" />
                <DropdownLabel>禁用</DropdownLabel>
              </DropdownItem>
            ) : (
              <DropdownItem>
                <Eye data-slot="icon" className="size-4" />
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

export default function KeysPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'disabled'>('all')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [selectedKey, setSelectedKey] = useState<ApiKey | null>(null)
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null)
  const [selectedModels, setSelectedModels] = useState<string[]>(['all'])

  const filteredKeys = apiKeys.filter((key) => {
    const matchesSearch =
      key.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      key.user.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || key.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const handleCreate = () => {
    // 模拟生成新 Key
    const newKey = `sk-cape-new-${'x'.repeat(32)}`
    setNewKeyValue(newKey)
  }

  const handleEdit = (key: ApiKey) => {
    setSelectedKey(key)
    setSelectedModels(key.models)
    setIsCreateOpen(true)
  }

  const toggleModel = (modelId: string) => {
    if (modelId === 'all') {
      setSelectedModels(['all'])
    } else {
      setSelectedModels((prev) => {
        const filtered = prev.filter((m) => m !== 'all')
        if (filtered.includes(modelId)) {
          return filtered.filter((m) => m !== modelId)
        } else {
          return [...filtered, modelId]
        }
      })
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Heading>API 密钥</Heading>
          <Text className="mt-1 text-zinc-500">
            管理 API 密钥、权限和使用配额
          </Text>
        </div>
        <Button onClick={() => { setSelectedKey(null); setNewKeyValue(null); setSelectedModels(['all']); setIsCreateOpen(true) }}>
          <Plus className="size-4" />
          生成密钥
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-zinc-400" />
          <Input
            type="text"
            placeholder="搜索密钥..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
        >
          <option value="all">全部状态</option>
          <option value="active">启用</option>
          <option value="disabled">禁用</option>
        </Select>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Text className="text-zinc-500">总密钥数</Text>
          <p className="text-2xl font-semibold mt-1">{apiKeys.length}</p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Text className="text-zinc-500">启用中</Text>
          <p className="text-2xl font-semibold mt-1 text-green-600">
            {apiKeys.filter((k) => k.status === 'active').length}
          </p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Text className="text-zinc-500">总调用量</Text>
          <p className="text-2xl font-semibold mt-1">
            {apiKeys.reduce((acc, k) => acc + k.usedTokens, 0).toLocaleString()}
          </p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Text className="text-zinc-500">平均速率限制</Text>
          <p className="text-2xl font-semibold mt-1">
            {Math.round(apiKeys.reduce((acc, k) => acc + k.rateLimit, 0) / apiKeys.length)} /min
          </p>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>名称</TableHeader>
              <TableHeader>密钥</TableHeader>
              <TableHeader>状态</TableHeader>
              <TableHeader>可用模型</TableHeader>
              <TableHeader>使用量</TableHeader>
              <TableHeader>最后使用</TableHeader>
              <TableHeader className="w-12"></TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredKeys.map((key) => (
              <KeyRow key={key.id} apiKey={key} onEdit={handleEdit} />
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={isCreateOpen} onClose={setIsCreateOpen}>
        <DialogTitle>{selectedKey ? '编辑密钥' : '生成新密钥'}</DialogTitle>
        <DialogDescription>
          {selectedKey ? '修改密钥配置' : '创建新的 API 密钥'}
        </DialogDescription>
        <DialogBody>
          {newKeyValue && (
            <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
              <Text className="text-green-800 dark:text-green-200 font-medium mb-2">
                新密钥已生成，请妥善保存：
              </Text>
              <code className="block text-sm font-mono bg-white dark:bg-zinc-900 p-3 rounded border break-all">
                {newKeyValue}
              </code>
              <Text className="text-green-700 dark:text-green-300 text-sm mt-2">
                此密钥只会显示一次，请立即复制保存
              </Text>
            </div>
          )}

          <Fieldset>
            <Field>
              <Label>名称</Label>
              <Input
                type="text"
                placeholder="例如：生产环境 Key"
                defaultValue={selectedKey?.name}
              />
              <Description>便于识别的密钥名称</Description>
            </Field>

            <Field>
              <Label>绑定用户</Label>
              <Select defaultValue={selectedKey?.user || ''}>
                <option value="">选择用户</option>
                <option value="admin@example.com">admin@example.com</option>
                <option value="developer@company.com">developer@company.com</option>
                <option value="test@demo.com">test@demo.com</option>
              </Select>
            </Field>

            <Field>
              <Label>可用模型</Label>
              <div className="space-y-2 mt-2">
                <CheckboxField>
                  <Checkbox
                    checked={selectedModels.includes('all')}
                    onChange={() => toggleModel('all')}
                  />
                  <Label>全部模型</Label>
                </CheckboxField>
                {!selectedModels.includes('all') && (
                  <div className="grid grid-cols-2 gap-2 pl-6">
                    {availableModels.map((model) => (
                      <CheckboxField key={model.id}>
                        <Checkbox
                          checked={selectedModels.includes(model.id)}
                          onChange={() => toggleModel(model.id)}
                        />
                        <Label>{model.name}</Label>
                      </CheckboxField>
                    ))}
                  </div>
                )}
              </div>
            </Field>

            <Field>
              <Label>速率限制</Label>
              <Input
                type="number"
                placeholder="100"
                defaultValue={selectedKey?.rateLimit || 100}
              />
              <Description>每分钟最大请求次数</Description>
            </Field>

            <Field>
              <Label>Token 配额</Label>
              <Input
                type="number"
                placeholder="-1 表示无限"
                defaultValue={selectedKey?.totalTokens}
              />
              <Description>总 Token 使用限制，-1 表示无限制</Description>
            </Field>

            <Field>
              <Label>过期时间</Label>
              <Input
                type="date"
                defaultValue={selectedKey?.expiresAt || ''}
              />
              <Description>留空表示永不过期</Description>
            </Field>
          </Fieldset>
        </DialogBody>
        <DialogActions>
          <Button plain onClick={() => setIsCreateOpen(false)}>
            取消
          </Button>
          {!selectedKey && !newKeyValue && (
            <Button onClick={handleCreate}>
              生成密钥
            </Button>
          )}
          {(selectedKey || newKeyValue) && (
            <Button onClick={() => setIsCreateOpen(false)}>
              {selectedKey ? '保存' : '完成'}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </div>
  )
}
