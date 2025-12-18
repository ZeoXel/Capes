'use client'

import { useState } from 'react'
import {
  Search,
  Plus,
  MoreHorizontal,
  Mail,
  Shield,
  Ban,
  Trash2,
  Edit,
  DollarSign,
} from 'lucide-react'
import { Heading } from '@/components/catalyst/heading'
import { Text } from '@/components/catalyst/text'
import { Badge } from '@/components/catalyst/badge'
import { Button } from '@/components/catalyst/button'
import { Input } from '@/components/catalyst/input'
import { Avatar } from '@/components/catalyst/avatar'
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
const users = [
  {
    id: '1',
    email: 'admin@example.com',
    name: '管理员',
    role: 'admin',
    status: 'active',
    balance: 1000.00,
    quota: -1,
    usedQuota: 45231,
    createdAt: '2024-01-15',
    lastActive: '刚刚',
  },
  {
    id: '2',
    email: 'developer@company.com',
    name: 'Dev Team',
    role: 'user',
    status: 'active',
    balance: 250.50,
    quota: 500000,
    usedQuota: 123456,
    createdAt: '2024-02-20',
    lastActive: '5 分钟前',
  },
  {
    id: '3',
    email: 'test@demo.com',
    name: '测试用户',
    role: 'user',
    status: 'active',
    balance: 50.00,
    quota: 100000,
    usedQuota: 89000,
    createdAt: '2024-03-10',
    lastActive: '1 小时前',
  },
  {
    id: '4',
    email: 'suspended@user.com',
    name: '已停用',
    role: 'user',
    status: 'suspended',
    balance: 0,
    quota: 50000,
    usedQuota: 50000,
    createdAt: '2024-01-20',
    lastActive: '3 天前',
  },
  {
    id: '5',
    email: 'new@user.com',
    name: '新用户',
    role: 'user',
    status: 'active',
    balance: 10.00,
    quota: 10000,
    usedQuota: 1200,
    createdAt: '2024-12-01',
    lastActive: '2 小时前',
  },
]

type User = typeof users[0]

function UserRow({ user, onEdit, onRecharge }: { user: User; onEdit: (user: User) => void; onRecharge: (user: User) => void }) {
  const quotaPercentage = user.quota === -1 ? 0 : (user.usedQuota / user.quota) * 100
  const isQuotaWarning = user.quota !== -1 && quotaPercentage > 80

  return (
    <TableRow>
      <TableCell>
        <div className="flex items-center gap-3">
          <Avatar
            initials={user.name.slice(0, 2).toUpperCase()}
            className="size-9 bg-zinc-200 dark:bg-zinc-700"
          />
          <div>
            <p className="font-medium text-zinc-900 dark:text-white">{user.name}</p>
            <p className="text-sm text-zinc-500">{user.email}</p>
          </div>
        </div>
      </TableCell>
      <TableCell>
        <Badge color={user.role === 'admin' ? 'purple' : 'zinc'}>
          {user.role === 'admin' ? '管理员' : '用户'}
        </Badge>
      </TableCell>
      <TableCell>
        <Badge color={user.status === 'active' ? 'green' : 'red'}>
          {user.status === 'active' ? '正常' : '已停用'}
        </Badge>
      </TableCell>
      <TableCell className="text-right tabular-nums font-medium">
        ${user.balance.toFixed(2)}
      </TableCell>
      <TableCell>
        <div className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className={isQuotaWarning ? 'text-amber-600' : 'text-zinc-500'}>
              {user.usedQuota.toLocaleString()}
            </span>
            <span className="text-zinc-400">
              / {user.quota === -1 ? '无限' : user.quota.toLocaleString()}
            </span>
          </div>
          {user.quota !== -1 && (
            <div className="h-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  quotaPercentage > 90 ? 'bg-red-500' :
                  quotaPercentage > 80 ? 'bg-amber-500' : 'bg-blue-500'
                }`}
                style={{ width: `${Math.min(quotaPercentage, 100)}%` }}
              />
            </div>
          )}
        </div>
      </TableCell>
      <TableCell className="text-zinc-500">{user.lastActive}</TableCell>
      <TableCell>
        <Dropdown>
          <DropdownButton plain>
            <MoreHorizontal className="size-4" />
          </DropdownButton>
          <DropdownMenu anchor="bottom end">
            <DropdownItem onClick={() => onEdit(user)}>
              <Edit data-slot="icon" className="size-4" />
              <DropdownLabel>编辑</DropdownLabel>
            </DropdownItem>
            <DropdownItem onClick={() => onRecharge(user)}>
              <DollarSign data-slot="icon" className="size-4" />
              <DropdownLabel>充值</DropdownLabel>
            </DropdownItem>
            <DropdownItem>
              <Mail data-slot="icon" className="size-4" />
              <DropdownLabel>发送邮件</DropdownLabel>
            </DropdownItem>
            <DropdownDivider />
            {user.status === 'active' ? (
              <DropdownItem>
                <Ban data-slot="icon" className="size-4" />
                <DropdownLabel>停用账户</DropdownLabel>
              </DropdownItem>
            ) : (
              <DropdownItem>
                <Shield data-slot="icon" className="size-4" />
                <DropdownLabel>恢复账户</DropdownLabel>
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

export default function UsersPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'suspended'>('all')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [isRechargeOpen, setIsRechargeOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)

  const filteredUsers = users.filter((user) => {
    const matchesSearch =
      user.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || user.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const handleRecharge = (user: User) => {
    setSelectedUser(user)
    setIsRechargeOpen(true)
  }

  const handleEdit = (user: User) => {
    setSelectedUser(user)
    setIsCreateOpen(true)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Heading>用户管理</Heading>
          <Text className="mt-1 text-zinc-500">
            管理系统用户、配额和余额
          </Text>
        </div>
        <Button onClick={() => { setSelectedUser(null); setIsCreateOpen(true) }}>
          <Plus className="size-4" />
          添加用户
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-zinc-400" />
          <Input
            type="text"
            placeholder="搜索用户..."
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
          <option value="active">正常</option>
          <option value="suspended">已停用</option>
        </Select>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Text className="text-zinc-500">总用户</Text>
          <p className="text-2xl font-semibold mt-1">{users.length}</p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Text className="text-zinc-500">活跃用户</Text>
          <p className="text-2xl font-semibold mt-1 text-green-600">
            {users.filter((u) => u.status === 'active').length}
          </p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Text className="text-zinc-500">总余额</Text>
          <p className="text-2xl font-semibold mt-1">
            ${users.reduce((acc, u) => acc + u.balance, 0).toFixed(2)}
          </p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Text className="text-zinc-500">总配额使用</Text>
          <p className="text-2xl font-semibold mt-1">
            {users.reduce((acc, u) => acc + u.usedQuota, 0).toLocaleString()}
          </p>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>用户</TableHeader>
              <TableHeader>角色</TableHeader>
              <TableHeader>状态</TableHeader>
              <TableHeader className="text-right">余额</TableHeader>
              <TableHeader>配额</TableHeader>
              <TableHeader>最后活跃</TableHeader>
              <TableHeader className="w-12"></TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredUsers.map((user) => (
              <UserRow
                key={user.id}
                user={user}
                onEdit={handleEdit}
                onRecharge={handleRecharge}
              />
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={isCreateOpen} onClose={setIsCreateOpen}>
        <DialogTitle>{selectedUser ? '编辑用户' : '添加用户'}</DialogTitle>
        <DialogDescription>
          {selectedUser ? '修改用户信息和配置' : '创建新用户账户'}
        </DialogDescription>
        <DialogBody>
          <Fieldset>
            <Field>
              <Label>邮箱</Label>
              <Input
                type="email"
                placeholder="user@example.com"
                defaultValue={selectedUser?.email}
              />
            </Field>
            <Field>
              <Label>用户名</Label>
              <Input
                type="text"
                placeholder="显示名称"
                defaultValue={selectedUser?.name}
              />
            </Field>
            <Field>
              <Label>角色</Label>
              <Select defaultValue={selectedUser?.role || 'user'}>
                <option value="user">普通用户</option>
                <option value="admin">管理员</option>
              </Select>
            </Field>
            <Field>
              <Label>配额限制</Label>
              <Input
                type="number"
                placeholder="-1 表示无限"
                defaultValue={selectedUser?.quota}
              />
              <Description>每月 Token 使用限制，-1 表示无限制</Description>
            </Field>
            {!selectedUser && (
              <Field>
                <Label>初始余额</Label>
                <Input type="number" placeholder="0.00" step="0.01" />
              </Field>
            )}
          </Fieldset>
        </DialogBody>
        <DialogActions>
          <Button plain onClick={() => setIsCreateOpen(false)}>
            取消
          </Button>
          <Button onClick={() => setIsCreateOpen(false)}>
            {selectedUser ? '保存' : '创建'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Recharge Dialog */}
      <Dialog open={isRechargeOpen} onClose={setIsRechargeOpen}>
        <DialogTitle>账户充值</DialogTitle>
        <DialogDescription>
          为 {selectedUser?.email} 充值
        </DialogDescription>
        <DialogBody>
          <Fieldset>
            <Field>
              <Label>当前余额</Label>
              <Text className="font-semibold">${selectedUser?.balance.toFixed(2)}</Text>
            </Field>
            <Field>
              <Label>充值金额</Label>
              <Input type="number" placeholder="0.00" step="0.01" />
            </Field>
            <Field>
              <Label>备注</Label>
              <Input type="text" placeholder="可选备注信息" />
            </Field>
          </Fieldset>
        </DialogBody>
        <DialogActions>
          <Button plain onClick={() => setIsRechargeOpen(false)}>
            取消
          </Button>
          <Button color="green" onClick={() => setIsRechargeOpen(false)}>
            确认充值
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  )
}
