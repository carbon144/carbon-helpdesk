export interface Task {
  id: string
  title: string
  description?: string
  completed: boolean
  priority: 'low' | 'medium' | 'high' | 'urgent'
  category: string
  dueDate?: string
  createdAt: string
}

export interface Habit {
  id: string
  name: string
  icon: string
  frequency: 'daily' | 'weekly'
  completedDates: string[]
  createdAt: string
}

export interface Goal {
  id: string
  title: string
  description?: string
  targetDate?: string
  progress: number // 0-100
  milestones: Milestone[]
  createdAt: string
}

export interface Milestone {
  id: string
  title: string
  completed: boolean
}
