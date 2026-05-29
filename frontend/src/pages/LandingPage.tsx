import { useEffect, useRef, useState, type ReactNode, type TransitionEvent } from 'react'
import { ButtonPrimary, Caption, Glass, Icon, Label, MeshBackground, TOKENS } from '../glass'
import { ScaledCanvas } from '../components/layout/ScaledCanvas'
import type { StoredSession } from '../store'
import { getSavedSession } from '../lib/api'

const LINKS = {
  doi: 'https://doi.org/10.XXXXX/ragmodex',
  github: 'https://github.com/vinvig/ragmodex',
  linkedin: 'https://linkedin.com/in/vincenzovigna',
}

interface LandingPageProps {
  onEnter: (restoreSession?: StoredSession) => void
  onSetup?: () => void
}

interface LandingArtboardProps {
  hasPreviousSession: boolean
  lastUsed: string
  model: string
  datasetSize: string
  fingerprint: string
  version?: string
  onRestore: () => void
  onStartFresh: () => void
  onOpenPaper: () => void
  onOpenGithub: () => void
  onOpenLinkedIn: () => void
}

function CapabilityChip({ icon, label, hue }: { icon: string; label: string; hue: string }) {
  const [title, sub] = label.split(' - ').map(part => part.trim())

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '12px 16px 12px 12px',
      background: `linear-gradient(180deg, oklch(96% 0.04 ${hue} / 0.9), oklch(93% 0.05 ${hue} / 0.75))`,
      backdropFilter: 'blur(30px) saturate(170%)',
      WebkitBackdropFilter: 'blur(30px) saturate(170%)',
      borderRadius: 14,
      boxShadow: `0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px oklch(65% 0.11 ${hue} / 0.22), 0 6px 16px -10px oklch(55% 0.13 ${hue} / 0.30)`,
      color: `oklch(36% 0.09 ${hue})`,
      minWidth: 0,
    }}>
      <div style={{
        width: 30, height: 30, borderRadius: 9,
        background: `oklch(65% 0.11 ${hue} / 0.18)`,
        display: 'grid', placeItems: 'center',
        flex: '0 0 30px',
      }}>
        <Icon name={icon} size={15} />
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{
          fontFamily: TOKENS.fontText, fontSize: 13, fontWeight: 700,
          letterSpacing: '-0.005em', color: `oklch(28% 0.08 ${hue})`,
        }}>{title}</div>
        <div style={{
          fontFamily: TOKENS.fontText, fontSize: 11, marginTop: 1, fontWeight: 500,
          color: `oklch(45% 0.07 ${hue})`,
        }}>{sub}</div>
      </div>
    </div>
  )
}

function ResourceLink({
  icon,
  label,
  sub,
  onClick,
}: {
  icon: string
  label: string
  sub?: string
  onClick: () => void
}) {
  return (
    <button type="button" onClick={onClick} style={{
      appearance: 'none',
      border: 'none',
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '9px 14px 9px 11px',
      background: 'rgba(255,255,255,0.55)',
      backdropFilter: 'blur(20px) saturate(160%)',
      WebkitBackdropFilter: 'blur(20px) saturate(160%)',
      borderRadius: 999,
      boxShadow: '0 1px 0 rgba(255,255,255,0.8) inset, 0 0 0 1px rgba(15,18,28,0.06)',
      cursor: 'pointer',
    }}>
      <span style={{ color: TOKENS.accent, display: 'flex' }}><Icon name={icon} size={14} /></span>
      <span style={{
        fontFamily: TOKENS.fontText, fontSize: 13, fontWeight: 600,
        color: TOKENS.ink, letterSpacing: '-0.005em',
      }}>{label}</span>
      {sub && (
        <span style={{
          fontFamily: TOKENS.fontMono, fontSize: 10.5, color: TOKENS.inkFaint,
          padding: '2px 7px', borderRadius: 6,
          background: 'rgba(15,18,28,0.05)',
        }}>{sub}</span>
      )}
    </button>
  )
}

function SessionMetaRow({ icon, label, value }: { icon: string; label: string; value: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '11px 14px',
      background: 'rgba(255,255,255,0.55)',
      borderRadius: 12,
      boxShadow: '0 1px 0 rgba(255,255,255,0.8) inset, 0 0 0 1px rgba(15,18,28,0.05)',
    }}>
      <div style={{
        width: 28, height: 28, borderRadius: 8,
        background: 'oklch(66% 0.115 155 / 0.14)',
        color: TOKENS.accentInk,
        display: 'grid', placeItems: 'center',
        flex: '0 0 28px',
      }}>
        <Icon name={icon} size={14} />
      </div>
      <div style={{
        fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.inkMuted, fontWeight: 500,
      }}>{label}</div>
      <div style={{ flex: 1 }} />
      <div style={{
        fontFamily: TOKENS.fontMono, fontSize: 12.5, color: TOKENS.ink, fontWeight: 600,
      }}>{value}</div>
    </div>
  )
}

function LandingButton({
  children,
  icon,
  onClick,
}: {
  children: ReactNode
  icon: string
  onClick: () => void
}) {
  return (
    <button type="button" onClick={onClick} style={{
      appearance: 'none', border: 'none', cursor: 'pointer',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
      height: 44, width: '100%',
      borderRadius: 13,
      background: 'rgba(255,255,255,0.45)',
      color: TOKENS.inkSoft,
      fontFamily: TOKENS.fontText, fontSize: 14, fontWeight: 600, letterSpacing: '-0.005em',
      boxShadow: '0 1px 0 rgba(255,255,255,0.8) inset, 0 0 0 1px rgba(15,18,28,0.06)',
    }}>
      <Icon name={icon} size={15} />
      {children}
    </button>
  )
}

function LandingArtboard({
  hasPreviousSession,
  lastUsed,
  model,
  datasetSize,
  fingerprint,
  version = 'v0.4 - preprint',
  onRestore,
  onStartFresh,
  onOpenPaper,
  onOpenGithub,
  onOpenLinkedIn,
}: LandingArtboardProps) {
  return (
    <div style={{
      width: 1440, height: 1024,
      position: 'relative',
      fontFamily: TOKENS.fontText,
      color: TOKENS.ink,
    }}>
      <MeshBackground style={undefined}>
        <div style={{
          position: 'absolute', top: 22, left: 28, right: 28,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          zIndex: 2,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <img
              src="/logo_ragmodex.png?v=20260524"
              alt="RAGMODEX"
              style={{ width: 30, height: 30, borderRadius: 9, objectFit: 'contain', flexShrink: 0 }}
            />
            <div style={{
              fontFamily: TOKENS.fontDisplay, fontSize: 14.5, fontWeight: 700,
              letterSpacing: '-0.01em', color: TOKENS.ink,
            }}>RAGMODEX</div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Glass tone="C" radius={999} padding={0} onClick={undefined} style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '6px 12px',
              fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.inkMuted, fontWeight: 500,
            }}>
              <Icon name="info" size={13} />
              <span>{version}</span>
            </Glass>
          </div>
        </div>

        <div style={{
          position: 'absolute', inset: 0,
          display: 'grid', placeItems: 'center',
          padding: '60px 80px 120px',
        }}>
          <div style={{
            width: 920, display: 'flex', flexDirection: 'column',
            alignItems: 'center', gap: 28,
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '6px 14px 6px 8px',
              background: 'rgba(255,255,255,0.55)',
              backdropFilter: 'blur(20px) saturate(160%)',
              WebkitBackdropFilter: 'blur(20px) saturate(160%)',
              borderRadius: 999,
              boxShadow: '0 1px 0 rgba(255,255,255,0.8) inset, 0 0 0 1px rgba(15,18,28,0.05)',
            }}>
              <span style={{
                width: 22, height: 22, borderRadius: 7,
                background: 'oklch(66% 0.115 155 / 0.14)',
                color: TOKENS.accentInk,
                display: 'grid', placeItems: 'center',
              }}>
                <Icon name="sparkle" size={12} />
              </span>
              <span style={{
                fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 600,
                letterSpacing: '0.10em', textTransform: 'uppercase', color: TOKENS.inkSoft,
              }}>Drug discovery</span>
              <span style={{
                width: 3, height: 3, borderRadius: 999, background: TOKENS.inkFaint,
              }} />
              <span style={{
                fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 600,
                letterSpacing: '0.10em', textTransform: 'uppercase', color: TOKENS.inkMuted,
              }}>GLUT-1 research</span>
            </div>

            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18,
            }}>
              <img
                src="/logo_ragmodex.png?v=20260524"
                alt="RAGMODEX"
                style={{
                  width: 96,
                  height: 96,
                  borderRadius: 24,
                  objectFit: 'contain',
                }}
              />

              <h1 style={{
                margin: 0,
                fontFamily: TOKENS.fontDisplay,
                fontSize: 104, fontWeight: 700,
                letterSpacing: '-0.045em', lineHeight: 0.95,
                color: TOKENS.ink, textAlign: 'center',
              }}>RAGMODEX</h1>

              <div style={{
                fontFamily: TOKENS.fontDisplay,
                fontSize: 22, fontWeight: 500,
                letterSpacing: '-0.015em', lineHeight: 1.35,
                color: TOKENS.inkSoft, textAlign: 'center', maxWidth: 760,
              }}>
                Retrieval Augmented Generation for{' '}
                <span style={{ color: TOKENS.accent, fontWeight: 600 }}>Molecular Design</span>
                {' '}and{' '}
                <span style={{
                  background: 'linear-gradient(90deg, oklch(60% 0.13 200), oklch(55% 0.14 250))',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                  fontWeight: 600,
                }}>eXplainable AI</span>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <ResourceLink icon="file" label="Paper" sub="preprint" onClick={onOpenPaper} />
              <ResourceLink icon="cpu" label="GitHub" onClick={onOpenGithub} />
              <ResourceLink icon="info" label="LinkedIn" onClick={onOpenLinkedIn} />
            </div>

            {hasPreviousSession ? (
              <Glass tone="A" radius={24} padding={0} onClick={undefined} style={{ width: 560, marginTop: 6 }}>
                <div style={{
                  padding: '24px 24px 20px',
                  display: 'flex', flexDirection: 'column', gap: 18,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div style={{
                      width: 44, height: 44, borderRadius: 13,
                      background: 'linear-gradient(180deg, oklch(96% 0.04 155 / 0.9), oklch(92% 0.06 155 / 0.7))',
                      color: TOKENS.accentInk,
                      display: 'grid', placeItems: 'center',
                      boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px oklch(66% 0.115 155 / 0.22)',
                    }}>
                      <Icon name="check" size={20} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{
                        fontFamily: TOKENS.fontText, fontSize: 15, fontWeight: 600,
                        color: TOKENS.ink, letterSpacing: '-0.005em',
                      }}>Previous session found</div>
                      <div style={{
                        fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.inkMuted, marginTop: 2,
                      }}>Last saved {lastUsed} - manual save</div>
                    </div>
                    <div style={{
                      padding: '4px 10px', borderRadius: 7,
                      background: 'oklch(66% 0.115 155 / 0.14)',
                      color: TOKENS.accentInk,
                      fontFamily: TOKENS.fontText, fontSize: 10.5, fontWeight: 700,
                      letterSpacing: '0.08em', textTransform: 'uppercase',
                    }}>Ready</div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <SessionMetaRow icon="cpu" label="Model" value={model} />
                    <SessionMetaRow icon="db" label="Dataset" value={datasetSize} />
                    <SessionMetaRow icon="sliders" label="Fingerprint" value={fingerprint} />
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <ButtonPrimary icon="chevRight" full disabled={false} onClick={onRestore}>Restore session</ButtonPrimary>
                    <LandingButton icon="plus" onClick={onStartFresh}>Start a fresh session</LandingButton>
                  </div>
                </div>
              </Glass>
            ) : (
              <Glass tone="A" radius={24} padding={28} onClick={undefined} style={{ width: 560, marginTop: 6 }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16, alignItems: 'stretch' }}>
                  <div style={{ textAlign: 'center' }}>
                    <Label style={{ color: TOKENS.accent, marginBottom: 8 }}>NEW WORKSPACE</Label>
                    <div style={{
                      fontFamily: TOKENS.fontDisplay, fontSize: 20, fontWeight: 600,
                      color: TOKENS.ink, letterSpacing: '-0.015em',
                    }}>Start by uploading a model</div>
                    <Caption style={{ marginTop: 6 }}>
                      Drop a trained classifier and CSV datasets to begin.
                    </Caption>
                  </div>
                  <ButtonPrimary icon="upload" full disabled={false} onClick={onStartFresh}>Open setup</ButtonPrimary>
                </div>
              </Glass>
            )}
          </div>
        </div>

        <div style={{
          position: 'absolute', left: 28, right: 28, bottom: 22,
          display: 'flex', alignItems: 'center', gap: 14,
        }}>
          <div style={{
            flex: 1, display: 'grid',
            gridTemplateColumns: 'repeat(5, 1fr)',
            gap: 10,
          }}>
            <CapabilityChip icon="flask" label="Predict - Bioactivity classifier" hue="295" />
            <CapabilityChip icon="layers" label="Design - Novel molecules" hue="25" />
            <CapabilityChip icon="search" label="Screen - Virtual library" hue="220" />
            <CapabilityChip icon="chart" label="Evaluate - ROC, PR, SHAP" hue="55" />
            <CapabilityChip icon="sparkle" label="Explain - LLM rationale" hue="155" />
          </div>
        </div>

        <div style={{
          position: 'absolute', left: 0, right: 0, bottom: 4,
          display: 'flex', justifyContent: 'center',
          fontFamily: TOKENS.fontMono, fontSize: 10.5, letterSpacing: '0.18em',
          color: TOKENS.inkFaint, textTransform: 'uppercase',
        }}>
          Drug Discovery <span style={{ margin: '0 10px', opacity: 0.5 }}>|</span> GLUT-1 Research
        </div>
      </MeshBackground>
    </div>
  )
}

function openLink(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

function getLastUsed(session: StoredSession) {
  const diff = Date.now() - session.savedAt
  const days = Math.floor(diff / 86_400_000)
  const hours = Math.floor(diff / 3_600_000)
  const minutes = Math.floor(diff / 60_000)

  if (days >= 1) return `${days} day${days > 1 ? 's' : ''} ago`
  if (hours >= 1) return `${hours}h ago`
  if (minutes >= 1) return `${minutes} minutes ago`
  return 'recently'
}

export function LandingPage({ onEnter, onSetup }: LandingPageProps) {
  const [session, setSession] = useState<StoredSession | null>(null)
  const [sliding, setSliding] = useState(false)
  const [visible, setVisible] = useState(true)
  const restoreRef = useRef<StoredSession | undefined>(undefined)

  useEffect(() => {
    let cancelled = false
    getSavedSession()
      .then(saved => {
        if (cancelled) return
        if (saved.exists && (saved.model_loaded || saved.training_data)) {
          setSession({
            modelLoaded: !!saved.model_loaded,
            trainingData: !!saved.training_data,
            testData: !!saved.test_data,
            modelName: String(saved.model_name ?? ''),
            nMolecules: Number(saved.n_molecules ?? 0),
            nTest: Number(saved.n_test ?? 0),
            fpRadius: Number(saved.fp_radius ?? 3),
            fpNbits: Number(saved.fp_nbits ?? 2048),
            llmProvider: '',
            llmModel: '',
            temperature: 0.3,
            savedAt: saved.saved_at ? Date.parse(saved.saved_at) : Date.now(),
          })
        } else {
          setSession(null)
        }
      })
      .catch(() => {
        if (!cancelled) setSession(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  function dismiss(restore?: StoredSession) {
    restoreRef.current = restore
    setSliding(true)
  }

  function handleTransitionEnd(event: TransitionEvent<HTMLDivElement>) {
    if (event.propertyName === 'transform' && sliding) {
      setVisible(false)
      onEnter(restoreRef.current)
    }
  }

  if (!visible) return null

  return (
    <div
      onTransitionEnd={handleTransitionEnd}
      className="fixed inset-0 z-[9999] overflow-auto"
      style={{
        background: '#eef0f4',
        transform: sliding ? 'translateY(-100%)' : 'translateY(0)',
        transition: 'transform 850ms cubic-bezier(0.65, 0, 0.35, 1)',
      }}
    >
      <ScaledCanvas>
        <LandingArtboard
          hasPreviousSession={!!session}
          lastUsed={session ? getLastUsed(session) : 'never'}
          model={session?.modelLoaded ? session.modelName || 'Model loaded' : 'No model loaded'}
          datasetSize={session?.trainingData ? `${session.nMolecules.toLocaleString()} molecules` : 'No dataset loaded'}
          fingerprint={`Morgan r${session?.fpRadius ?? 3} - ${session?.fpNbits ?? 2048}b`}
          onRestore={() => dismiss(session ?? undefined)}
          onStartFresh={() => {
            if (onSetup) {
              setVisible(false)
              onSetup()
            } else {
              dismiss()
            }
          }}
          onOpenPaper={() => openLink(LINKS.doi)}
          onOpenGithub={() => openLink(LINKS.github)}
          onOpenLinkedIn={() => openLink(LINKS.linkedin)}
        />
      </ScaledCanvas>
    </div>
  )
}

