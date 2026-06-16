import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cn } from '@/lib/utils';

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'default' | 'secondary' | 'ghost' | 'outline' | 'destructive';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  asChild?: boolean;
};

export function Button({ className, variant = 'default', size = 'default', asChild = false, ...props }: ButtonProps) {
  const variants: Record<NonNullable<ButtonProps['variant']>, string> = {
    default: 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm',
    secondary: 'border border-slate-200 bg-slate-100 text-slate-900 hover:bg-slate-200',
    ghost: 'bg-transparent text-slate-700 hover:bg-slate-100 hover:text-slate-950',
    outline: 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 hover:text-slate-950',
    destructive: 'bg-red-600 text-white hover:bg-red-700 shadow-sm',
  };
  const sizes: Record<NonNullable<ButtonProps['size']>, string> = {
    default: 'h-10 px-4 py-2',
    sm: 'h-8 rounded-lg px-3 text-xs',
    lg: 'h-11 px-5',
    icon: 'h-10 w-10 p-0',
  };

  const Comp = asChild ? Slot : 'button';

  return (
    <Comp
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-xl text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-blue-500/40 disabled:cursor-not-allowed disabled:opacity-50',
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  );
}
