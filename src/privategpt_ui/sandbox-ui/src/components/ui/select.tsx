import * as React from "react"

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  children?: React.ReactNode
}

export interface SelectTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children?: React.ReactNode
}

export interface SelectContentProps {
  children?: React.ReactNode
}

export interface SelectItemProps extends React.OptionHTMLAttributes<HTMLOptionElement> {
  children?: React.ReactNode
}

export interface SelectValueProps {
  placeholder?: string
}

export function Select({ children, ...props }: SelectProps) {
  return (
    <select 
      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
      {...props}
    >
      {children}
    </select>
  )
}

export function SelectTrigger({ children, className = "", ...props }: SelectTriggerProps) {
  return (
    <button
      className={`flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export function SelectContent({ children }: SelectContentProps) {
  return <>{children}</>
}

export function SelectItem({ children, ...props }: SelectItemProps) {
  return (
    <option {...props}>
      {children}
    </option>
  )
}

export function SelectValue({ placeholder }: SelectValueProps) {
  return <span>{placeholder}</span>
}