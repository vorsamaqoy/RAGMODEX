import type { SVGProps } from 'react'

interface IcoProps extends SVGProps<SVGSVGElement> {
  size?: number
  sw?: number
  d?: string
}

const Ico = ({ d, size = 18, fill = 'none', stroke = 'currentColor', sw = 1.5, children, ...rest }: IcoProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={stroke}
       strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" {...rest}>
    {d ? <path d={d} /> : children}
  </svg>
)

export type IconProps = Omit<IcoProps, 'd'>

export const I = {
  Logo: (p: IconProps) => (
    <Ico size={p.size ?? 22} stroke="var(--accent-blue-deep)" sw={1.6} {...p}>
      <path d="M12 2 L21 7 L21 17 L12 22 L3 17 L3 7 Z" />
      <circle cx="12" cy="12" r="2.2" fill="var(--accent-blue-deep)" stroke="none" />
      <circle cx="7" cy="9" r="1.1" fill="var(--accent-blue-deep)" stroke="none" />
      <circle cx="17" cy="9" r="1.1" fill="var(--accent-blue-deep)" stroke="none" />
      <circle cx="7" cy="15" r="1.1" fill="var(--accent-blue-deep)" stroke="none" />
      <circle cx="17" cy="15" r="1.1" fill="var(--accent-blue-deep)" stroke="none" />
      <path d="M12 12 L7 9 M12 12 L17 9 M12 12 L7 15 M12 12 L17 15" stroke="var(--accent-blue-deep)" />
    </Ico>
  ),
  Chat: (p: IconProps) => <Ico {...p} d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.4A8 8 0 1 1 21 12Z" />,
  Predict: (p: IconProps) => <Ico {...p}><path d="M3 17 L9 11 L13 14 L21 6"/><path d="M21 11 V6 H16"/></Ico>,
  Design: (p: IconProps) => <Ico {...p}><circle cx="6" cy="6" r="2.2"/><circle cx="18" cy="6" r="2.2"/><circle cx="12" cy="18" r="2.2"/><path d="M7.6 7.4 L10.8 16M16.4 7.4 L13.2 16M8 6h8"/></Ico>,
  Screen: (p: IconProps) => <Ico {...p}><circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/></Ico>,
  Eval: (p: IconProps) => <Ico {...p}><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></Ico>,
  Vis: (p: IconProps) => <Ico {...p}><circle cx="12" cy="12" r="3"/><path d="M2 12h4M18 12h4M12 2v4M12 18v4M5 5l3 3M16 16l3 3M19 5l-3 3M8 16l-3 3"/></Ico>,
  Settings: (p: IconProps) => <Ico {...p}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1A2 2 0 1 1 4.3 17l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1A2 2 0 1 1 7 4.3l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1A2 2 0 1 1 19.7 7l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/></Ico>,
  Bell: (p: IconProps) => <Ico {...p}><path d="M6 8a6 6 0 1 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9Z"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></Ico>,
  Search: (p: IconProps) => <Ico {...p}><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></Ico>,
  Plus: (p: IconProps) => <Ico {...p} d="M12 5v14M5 12h14" />,
  ArrowRight: (p: IconProps) => <Ico {...p} d="M5 12h14M13 6l6 6-6 6" />,
  ArrowUpRight: (p: IconProps) => <Ico {...p} d="M7 17 17 7M9 7h8v8" />,
  Send: (p: IconProps) => <Ico {...p}><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4Z"/></Ico>,
  Check: (p: IconProps) => <Ico {...p} d="M5 12l4 4L19 6" />,
  X: (p: IconProps) => <Ico {...p} d="M6 6l12 12M18 6 6 18" />,
  Chevron: (p: IconProps) => <Ico {...p} d="m9 6 6 6-6 6" />,
  ChevronDown: (p: IconProps) => <Ico {...p} d="m6 9 6 6 6-6" />,
  Sparkle: (p: IconProps) => <Ico {...p}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/></Ico>,
  Flask: (p: IconProps) => <Ico {...p}><path d="M9 3h6M10 3v6L4.5 18A2 2 0 0 0 6.2 21h11.6A2 2 0 0 0 19.5 18L14 9V3"/><path d="M7.5 14h9"/></Ico>,
  Doc: (p: IconProps) => <Ico {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/></Ico>,
  Refresh: (p: IconProps) => <Ico {...p}><path d="M3 12a9 9 0 0 1 15.5-6.3L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.5 6.3L3 16"/><path d="M3 21v-5h5"/></Ico>,
  Filter: (p: IconProps) => <Ico {...p} d="M3 5h18M6 12h12M10 19h4" />,
  Download: (p: IconProps) => <Ico {...p}><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></Ico>,
  Play: (p: IconProps) => <Ico {...p} fill="currentColor" stroke="none"><path d="M7 4v16l13-8z"/></Ico>,
  Pause: (p: IconProps) => <Ico {...p}><path d="M7 4v16M17 4v16"/></Ico>,
  Star: (p: IconProps) => <Ico {...p} d="M12 3 14.6 9 21 9.6 16 14 17.5 21 12 17.6 6.5 21 8 14 3 9.6 9.4 9Z" />,
  History: (p: IconProps) => <Ico {...p}><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/></Ico>,
  Cube: (p: IconProps) => <Ico {...p}><path d="M21 7 12 2 3 7v10l9 5 9-5z"/><path d="M3 7l9 5 9-5M12 22V12"/></Ico>,
  Bolt: (p: IconProps) => <Ico {...p} d="M13 2 3 14h7l-1 8 10-12h-7z" />,
  Sidebar: (p: IconProps) => <Ico {...p}><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></Ico>,
  Dot: (p: IconProps) => <Ico {...p} fill="currentColor" stroke="none"><circle cx="12" cy="12" r="3"/></Ico>,
  CircleCheck: (p: IconProps) => <Ico {...p}><circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5L15.5 10"/></Ico>,
  Warning: (p: IconProps) => <Ico {...p}><path d="M10.3 3.7 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.7a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></Ico>,
  Folder: (p: IconProps) => <Ico {...p}><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></Ico>,
  Database: (p: IconProps) => <Ico {...p}><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></Ico>,
  Brain: (p: IconProps) => <Ico {...p}><path d="M9 3a3 3 0 0 0-3 3v.3A3 3 0 0 0 4 9a3 3 0 0 0 1 2.2A3 3 0 0 0 4 14a3 3 0 0 0 2 2.8V18a3 3 0 0 0 6 0V3a3 3 0 0 0-3 0Z"/><path d="M15 3a3 3 0 0 1 3 3v.3A3 3 0 0 1 20 9a3 3 0 0 1-1 2.2A3 3 0 0 1 20 14a3 3 0 0 1-2 2.8V18a3 3 0 0 1-6 0V3a3 3 0 0 1 3 0Z"/></Ico>,
}
