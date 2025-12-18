'use client'

import { useState } from 'react'
import {
  Search,
  Plus,
  MoreHorizontal,
  Trash2,
  Edit,
  Copy,
  Calculator,
  Percent,
  DollarSign,
  Sparkles,
  Save,
} from 'lucide-react'
import { Heading, Subheading } from '@/components/catalyst/heading'
import { Text } from '@/components/catalyst/text'
import { Badge } from '@/components/catalyst/badge'
import { Button } from '@/components/catalyst/button'
import { Input } from '@/components/catalyst/input'
import { Divider } from '@/components/catalyst/divider'
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

// Mock data - 模型定价
const modelPricing = [
  {
    id: '1',
    model: 'gpt-4o',
    provider: 'OpenAI',
    inputPrice: 2.50,
    outputPrice: 10.00,
    multiplier: 1.0,
    finalInput: 2.50,
    finalOutput: 10.00,
    status: 'active',
  },
  {
    id: '2',
    model: 'gpt-4o-mini',
    provider: 'OpenAI',
    inputPrice: 0.15,
    outputPrice: 0.60,
    multiplier: 1.0,
    finalInput: 0.15,
    finalOutput: 0.60,
    status: 'active',
  },
  {
    id: '3',
    model: 'gpt-4-turbo',
    provider: 'OpenAI',
    inputPrice: 10.00,
    outputPrice: 30.00,
    multiplier: 1.0,
    finalInput: 10.00,
    finalOutput: 30.00,
    status: 'active',
  },
  {
    id: '4',
    model: 'claude-3-opus',
    provider: 'Anthropic',
    inputPrice: 15.00,
    outputPrice: 75.00,
    multiplier: 1.0,
    finalInput: 15.00,
    finalOutput: 75.00,
    status: 'active',
  },
  {
    id: '5',
    model: 'claude-3-sonnet',
    provider: 'Anthropic',
    inputPrice: 3.00,
    outputPrice: 15.00,
    multiplier: 1.0,
    finalInput: 3.00,
    finalOutput: 15.00,
    status: 'active',
  },
  {
    id: '6',
    model: 'claude-3-haiku',
    provider: 'Anthropic',
    inputPrice: 0.25,
    outputPrice: 1.25,
    multiplier: 1.0,
    finalInput: 0.25,
    finalOutput: 1.25,
    status: 'active',
  },
  {
    id: '7',
    model: 'gemini-2.5-flash',
    provider: 'Google',
    inputPrice: 0.075,
    outputPrice: 0.30,
    multiplier: 1.0,
    finalInput: 0.075,
    finalOutput: 0.30,
    status: 'active',
  },
  {
    id: '8',
    model: 'gemini-2.5-pro',
    provider: 'Google',
    inputPrice: 1.25,
    outputPrice: 5.00,
    multiplier: 1.0,
    finalInput: 1.25,
    finalOutput: 5.00,
    status: 'active',
  },
]

// 用户组倍率
const userGroups = [
  { id: '1', name: '免费用户', multiplier: 1.5, description: '未付费用户' },
  { id: '2', name: '基础会员', multiplier: 1.2, description: '月付会员' },
  { id: '3', name: '高级会员', multiplier: 1.0, description: '年付会员' },
  { id: '4', name: 'API 用户', multiplier: 0.9, description: 'API 调用用户' },
  { id: '5', name: '企业客户', multiplier: 0.8, description: '企业合作' },
]

// 能力定价
const capePricing = [
  { id: '1', name: '网页搜索', capeId: 'web-search', pricePerCall: 0.01, status: 'active' },
  { id: '2', name: '图像生成', capeId: 'image-gen', pricePerCall: 0.04, status: 'active' },
  { id: '3', name: '文档解析', capeId: 'doc-parser', pricePerCall: 0.02, status: 'active' },
  { id: '4', name: '代码执行', capeId: 'code-exec', pricePerCall: 0.005, status: 'active' },
  { id: '5', name: '视频生成', capeId: 'video-gen', pricePerCall: 0.50, status: 'disabled' },
]

type ModelPrice = typeof modelPricing[0]
type UserGroup = typeof userGroups[0]
type CapePrice = typeof capePricing[0]

function ModelPriceRow({ model, onEdit }: { model: ModelPrice; onEdit: (m: ModelPrice) => void }) {
  const providerColors: Record<string, string> = {
    'OpenAI': 'green',
    'Anthropic': 'orange',
    'Google': 'blue',
  }

  return (
    <TableRow>
      <TableCell>
        <div>
          <p className="font-medium text-zinc-900 dark:text-white">{model.model}</p>
          <Badge color={providerColors[model.provider] as any || 'zinc'} className="mt-1">
            {model.provider}
          </Badge>
        </div>
      </TableCell>
      <TableCell className="text-right tabular-nums">
        ${model.inputPrice.toFixed(3)}
      </TableCell>
      <TableCell className="text-right tabular-nums">
        ${model.outputPrice.toFixed(3)}
      </TableCell>
      <TableCell className="text-center">
        <Badge color={model.multiplier === 1.0 ? 'zinc' : 'blue'}>
          {model.multiplier}x
        </Badge>
      </TableCell>
      <TableCell className="text-right tabular-nums font-medium text-green-600">
        ${model.finalInput.toFixed(3)}
      </TableCell>
      <TableCell className="text-right tabular-nums font-medium text-green-600">
        ${model.finalOutput.toFixed(3)}
      </TableCell>
      <TableCell>
        <Dropdown>
          <DropdownButton plain>
            <MoreHorizontal className="size-4" />
          </DropdownButton>
          <DropdownMenu anchor="bottom end">
            <DropdownItem onClick={() => onEdit(model)}>
              <Edit data-slot="icon" className="size-4" />
              <DropdownLabel>编辑</DropdownLabel>
            </DropdownItem>
            <DropdownItem>
              <Copy data-slot="icon" className="size-4" />
              <DropdownLabel>复制</DropdownLabel>
            </DropdownItem>
            <DropdownDivider />
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

export default function PricingPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [providerFilter, setProviderFilter] = useState<string>('all')
  const [isModelEditOpen, setIsModelEditOpen] = useState(false)
  const [isGroupEditOpen, setIsGroupEditOpen] = useState(false)
  const [isCapeEditOpen, setIsCapeEditOpen] = useState(false)
  const [selectedModel, setSelectedModel] = useState<ModelPrice | null>(null)
  const [selectedGroup, setSelectedGroup] = useState<UserGroup | null>(null)
  const [selectedCape, setSelectedCape] = useState<CapePrice | null>(null)
  const [globalMultiplier, setGlobalMultiplier] = useState('1.0')

  const filteredModels = modelPricing.filter((model) => {
    const matchesSearch = model.model.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesProvider = providerFilter === 'all' || model.provider === providerFilter
    return matchesSearch && matchesProvider
  })

  const providers = [...new Set(modelPricing.map(m => m.provider))]

  const handleEditModel = (model: ModelPrice) => {
    setSelectedModel(model)
    setIsModelEditOpen(true)
  }

  const handleEditGroup = (group: UserGroup) => {
    setSelectedGroup(group)
    setIsGroupEditOpen(true)
  }

  const handleEditCape = (cape: CapePrice) => {
    setSelectedCape(cape)
    setIsCapeEditOpen(true)
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Heading>定价配置</Heading>
          <Text className="mt-1 text-zinc-500">
            配置模型定价、用户倍率和能力费用
          </Text>
        </div>
        <div className="flex items-center gap-2">
          <Button outline>
            <Calculator className="size-4" />
            价格计算器
          </Button>
          <Button>
            <Save className="size-4" />
            保存配置
          </Button>
        </div>
      </div>

      {/* Global Settings */}
      <div className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
        <Subheading className="mb-4">全局设置</Subheading>
        <div className="grid grid-cols-3 gap-6">
          <Field>
            <Label>全局倍率</Label>
            <Input
              type="number"
              step="0.1"
              value={globalMultiplier}
              onChange={(e) => setGlobalMultiplier(e.target.value)}
            />
            <Description>应用于所有模型的基础倍率</Description>
          </Field>
          <Field>
            <Label>计费单位</Label>
            <Select defaultValue="1m">
              <option value="1k">每 1K Token</option>
              <option value="1m">每 1M Token</option>
            </Select>
            <Description>价格显示单位</Description>
          </Field>
          <Field>
            <Label>货币</Label>
            <Select defaultValue="usd">
              <option value="usd">USD ($)</option>
              <option value="cny">CNY (¥)</option>
              <option value="eur">EUR (€)</option>
            </Select>
            <Description>定价货币单位</Description>
          </Field>
        </div>
      </div>

      {/* Model Pricing */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Subheading>模型定价</Subheading>
          <div className="flex items-center gap-4">
            <div className="relative max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-zinc-400" />
              <Input
                type="text"
                placeholder="搜索模型..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value)}
            >
              <option value="all">全部厂商</option>
              {providers.map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </Select>
            <Button outline onClick={() => { setSelectedModel(null); setIsModelEditOpen(true) }}>
              <Plus className="size-4" />
              添加模型
            </Button>
          </div>
        </div>

        <div className="rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900 overflow-hidden">
          <Table>
            <TableHead>
              <TableRow>
                <TableHeader>模型</TableHeader>
                <TableHeader className="text-right">输入价格</TableHeader>
                <TableHeader className="text-right">输出价格</TableHeader>
                <TableHeader className="text-center">倍率</TableHeader>
                <TableHeader className="text-right">最终输入</TableHeader>
                <TableHeader className="text-right">最终输出</TableHeader>
                <TableHeader className="w-12"></TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredModels.map((model) => (
                <ModelPriceRow key={model.id} model={model} onEdit={handleEditModel} />
              ))}
            </TableBody>
          </Table>
        </div>
        <Text className="text-xs text-zinc-500">
          * 价格单位：$/1M Token，最终价格 = 基础价格 × 模型倍率 × 全局倍率
        </Text>
      </div>

      {/* User Group Multipliers */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Subheading>用户组倍率</Subheading>
          <Button outline onClick={() => { setSelectedGroup(null); setIsGroupEditOpen(true) }}>
            <Plus className="size-4" />
            添加用户组
          </Button>
        </div>

        <div className="grid grid-cols-5 gap-4">
          {userGroups.map((group) => (
            <div
              key={group.id}
              className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-700 cursor-pointer transition-colors"
              onClick={() => handleEditGroup(group)}
            >
              <div className="flex items-center justify-between mb-2">
                <Percent className="size-5 text-zinc-400" />
                <Badge color={group.multiplier <= 1.0 ? 'green' : group.multiplier <= 1.2 ? 'blue' : 'amber'}>
                  {group.multiplier}x
                </Badge>
              </div>
              <p className="font-medium text-zinc-900 dark:text-white">{group.name}</p>
              <p className="text-sm text-zinc-500 mt-1">{group.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Cape Pricing */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Subheading>能力定价</Subheading>
          <Button outline onClick={() => { setSelectedCape(null); setIsCapeEditOpen(true) }}>
            <Plus className="size-4" />
            添加能力
          </Button>
        </div>

        <div className="rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900 overflow-hidden">
          <Table>
            <TableHead>
              <TableRow>
                <TableHeader>能力名称</TableHeader>
                <TableHeader>能力 ID</TableHeader>
                <TableHeader className="text-right">单次调用价格</TableHeader>
                <TableHeader>状态</TableHeader>
                <TableHeader className="w-12"></TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {capePricing.map((cape) => (
                <TableRow key={cape.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Sparkles className="size-4 text-blue-500" />
                      <span className="font-medium">{cape.name}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <code className="text-sm bg-zinc-100 dark:bg-zinc-800 px-2 py-1 rounded">
                      {cape.capeId}
                    </code>
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-medium">
                    ${cape.pricePerCall.toFixed(3)}
                  </TableCell>
                  <TableCell>
                    <Badge color={cape.status === 'active' ? 'green' : 'zinc'}>
                      {cape.status === 'active' ? '启用' : '禁用'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Dropdown>
                      <DropdownButton plain>
                        <MoreHorizontal className="size-4" />
                      </DropdownButton>
                      <DropdownMenu anchor="bottom end">
                        <DropdownItem onClick={() => handleEditCape(cape)}>
                          <Edit data-slot="icon" className="size-4" />
                          <DropdownLabel>编辑</DropdownLabel>
                        </DropdownItem>
                        <DropdownDivider />
                        <DropdownItem className="text-red-600">
                          <Trash2 data-slot="icon" className="size-4" />
                          <DropdownLabel>删除</DropdownLabel>
                        </DropdownItem>
                      </DropdownMenu>
                    </Dropdown>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Model Edit Dialog */}
      <Dialog open={isModelEditOpen} onClose={setIsModelEditOpen}>
        <DialogTitle>{selectedModel ? '编辑模型定价' : '添加模型'}</DialogTitle>
        <DialogDescription>
          配置模型的输入输出价格
        </DialogDescription>
        <DialogBody>
          <Fieldset>
            <Field>
              <Label>模型名称</Label>
              <Input
                type="text"
                placeholder="gpt-4o"
                defaultValue={selectedModel?.model}
              />
            </Field>
            <Field>
              <Label>提供商</Label>
              <Select defaultValue={selectedModel?.provider || 'OpenAI'}>
                <option value="OpenAI">OpenAI</option>
                <option value="Anthropic">Anthropic</option>
                <option value="Google">Google</option>
                <option value="Other">其他</option>
              </Select>
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field>
                <Label>输入价格 ($/1M)</Label>
                <Input
                  type="number"
                  step="0.001"
                  defaultValue={selectedModel?.inputPrice}
                />
              </Field>
              <Field>
                <Label>输出价格 ($/1M)</Label>
                <Input
                  type="number"
                  step="0.001"
                  defaultValue={selectedModel?.outputPrice}
                />
              </Field>
            </div>
            <Field>
              <Label>模型倍率</Label>
              <Input
                type="number"
                step="0.1"
                defaultValue={selectedModel?.multiplier || 1.0}
              />
              <Description>针对此模型的额外倍率调整</Description>
            </Field>
          </Fieldset>
        </DialogBody>
        <DialogActions>
          <Button plain onClick={() => setIsModelEditOpen(false)}>取消</Button>
          <Button onClick={() => setIsModelEditOpen(false)}>保存</Button>
        </DialogActions>
      </Dialog>

      {/* Group Edit Dialog */}
      <Dialog open={isGroupEditOpen} onClose={setIsGroupEditOpen}>
        <DialogTitle>{selectedGroup ? '编辑用户组' : '添加用户组'}</DialogTitle>
        <DialogDescription>
          配置用户组的定价倍率
        </DialogDescription>
        <DialogBody>
          <Fieldset>
            <Field>
              <Label>组名称</Label>
              <Input
                type="text"
                placeholder="高级会员"
                defaultValue={selectedGroup?.name}
              />
            </Field>
            <Field>
              <Label>倍率</Label>
              <Input
                type="number"
                step="0.1"
                defaultValue={selectedGroup?.multiplier || 1.0}
              />
              <Description>小于 1 表示折扣，大于 1 表示加价</Description>
            </Field>
            <Field>
              <Label>描述</Label>
              <Input
                type="text"
                placeholder="用户组描述"
                defaultValue={selectedGroup?.description}
              />
            </Field>
          </Fieldset>
        </DialogBody>
        <DialogActions>
          <Button plain onClick={() => setIsGroupEditOpen(false)}>取消</Button>
          <Button onClick={() => setIsGroupEditOpen(false)}>保存</Button>
        </DialogActions>
      </Dialog>

      {/* Cape Edit Dialog */}
      <Dialog open={isCapeEditOpen} onClose={setIsCapeEditOpen}>
        <DialogTitle>{selectedCape ? '编辑能力定价' : '添加能力'}</DialogTitle>
        <DialogDescription>
          配置 Cape 能力的调用费用
        </DialogDescription>
        <DialogBody>
          <Fieldset>
            <Field>
              <Label>能力名称</Label>
              <Input
                type="text"
                placeholder="网页搜索"
                defaultValue={selectedCape?.name}
              />
            </Field>
            <Field>
              <Label>能力 ID</Label>
              <Input
                type="text"
                placeholder="web-search"
                defaultValue={selectedCape?.capeId}
              />
            </Field>
            <Field>
              <Label>单次调用价格 ($)</Label>
              <Input
                type="number"
                step="0.001"
                defaultValue={selectedCape?.pricePerCall}
              />
            </Field>
          </Fieldset>
        </DialogBody>
        <DialogActions>
          <Button plain onClick={() => setIsCapeEditOpen(false)}>取消</Button>
          <Button onClick={() => setIsCapeEditOpen(false)}>保存</Button>
        </DialogActions>
      </Dialog>
    </div>
  )
}
