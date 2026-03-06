'use client'

import { Task, Habit, Goal } from '@/types'

const KEYS = {
  tasks: 'gmst_tasks',
  habits: 'gmst_habits',
  goals: 'gmst_goals',
}

function get<T>(key: string, fallback: T[]): T[] {
  if (typeof window === 'undefined') return fallback
  try {
    const data = localStorage.getItem(key)
    return data ? JSON.parse(data) : fallback
  } catch {
    return fallback
  }
}

function set<T>(key: string, data: T[]) {
  localStorage.setItem(key, JSON.stringify(data))
}

export function getTasks(): Task[] {
  return get<Task>(KEYS.tasks, [])
}
export function saveTasks(tasks: Task[]) {
  set(KEYS.tasks, tasks)
}

export function getHabits(): Habit[] {
  return get<Habit>(KEYS.habits, [])
}
export function saveHabits(habits: Habit[]) {
  set(KEYS.habits, habits)
}

export function getGoals(): Goal[] {
  return get<Goal>(KEYS.goals, [])
}
export function saveGoals(goals: Goal[]) {
  set(KEYS.goals, goals)
}
