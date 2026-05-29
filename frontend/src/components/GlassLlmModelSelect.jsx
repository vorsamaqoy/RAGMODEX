import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Icon, TOKENS } from '../glass';
import { getLlmCatalog, setLlmConfig } from '../lib/api';
import { useAppStore } from '../store';

export function GlassLlmModelSelect() {
  const { llmProvider, llmModel, temperature, setLlmStatus } = useAppStore();
  const [open, setOpen] = useState(false);
  const catalogQ = useQuery({ queryKey: ['llm-catalog'], queryFn: getLlmCatalog, staleTime: 15000 });

  const provider = catalogQ.data?.provider ?? llmProvider;
  const model = catalogQ.data?.model ?? llmModel;
  const currentProvider = catalogQ.data?.providers?.find(item => item.name === provider);
  const models = currentProvider?.models?.length ? currentProvider.models : [model].filter(Boolean);

  useEffect(() => {
    if (!catalogQ.data) return;
    setLlmStatus({
      provider: catalogQ.data.provider,
      model: catalogQ.data.model,
      temperature: catalogQ.data.temperature,
    });
  }, [catalogQ.data, setLlmStatus]);

  const saveMut = useMutation({
    mutationFn: nextModel => setLlmConfig(provider, nextModel, temperature),
    onSuccess: data => {
      setLlmStatus({ provider: data.provider, model: data.model, temperature });
      toast.success('LLM model saved');
      catalogQ.refetch();
    },
    onError: err => toast.error(String(err.message ?? err)),
  });

  return (
    <div style={{ position: 'relative', width: 250, zIndex: open ? 70 : 1 }}>
      <button
        type="button"
        aria-label="LLM model"
        onClick={event => {
          event.stopPropagation();
          setOpen(current => !current);
        }}
        style={{
          width: '100%',
          height: 34,
          display: 'flex',
          alignItems: 'center',
          gap: 9,
          padding: '0 10px 0 12px',
          border: 'none',
          borderRadius: 10,
          background: 'rgba(255,255,255,0.65)',
          backdropFilter: 'blur(20px) saturate(160%)',
          WebkitBackdropFilter: 'blur(20px) saturate(160%)',
          boxShadow: '0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px rgba(15,18,28,0.05)',
          cursor: 'pointer',
          color: TOKENS.ink,
        }}
      >
        <span style={{
          height: 22,
          padding: '0 8px',
          display: 'inline-flex',
          alignItems: 'center',
          borderRadius: 6,
          background: provider === 'local' ? 'oklch(66% 0.115 240 / 0.13)' : 'oklch(66% 0.115 155 / 0.12)',
          color: provider === 'local' ? 'oklch(40% 0.12 240)' : TOKENS.accentInk,
          fontFamily: TOKENS.fontText,
          fontSize: 10.5,
          fontWeight: 700,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}>
          {provider}
        </span>
        <span style={{
          flex: 1,
          minWidth: 0,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          textAlign: 'left',
          fontFamily: TOKENS.fontText,
          fontSize: 12.5,
          fontWeight: 600,
          color: TOKENS.ink,
          letterSpacing: '-0.005em',
        }}>
          {model}
        </span>
        <span style={{ width: 24, height: 24, display: 'grid', placeItems: 'center', color: TOKENS.inkMuted }}>
          <Icon name="chevDown" size={14}/>
        </span>
      </button>

      {open && (
        <div
          onClick={event => event.stopPropagation()}
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: 40,
            maxHeight: 260,
            overflowY: 'auto',
            padding: 6,
            borderRadius: 14,
            background: 'rgba(255,255,255,0.88)',
            backdropFilter: 'blur(26px) saturate(180%)',
            WebkitBackdropFilter: 'blur(26px) saturate(180%)',
            boxShadow: '0 18px 48px rgba(15,18,28,0.16), 0 0 0 1px rgba(15,18,28,0.08), 0 1px 0 rgba(255,255,255,0.9) inset',
          }}
        >
          {models.map(item => {
            const active = item === model;
            return (
              <button
                key={item}
                type="button"
                onClick={() => {
                  setOpen(false);
                  if (item !== model) saveMut.mutate(item);
                }}
                style={{
                  width: '100%',
                  minHeight: 34,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '7px 10px',
                  border: 'none',
                  borderRadius: 10,
                  background: active ? 'oklch(66% 0.115 155 / 0.13)' : 'transparent',
                  color: active ? TOKENS.accentInk : TOKENS.inkSoft,
                  cursor: 'pointer',
                  fontFamily: TOKENS.fontText,
                  fontSize: 12.5,
                  fontWeight: active ? 700 : 600,
                  textAlign: 'left',
                }}
              >
                <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item}</span>
                {active && <Icon name="check" size={14}/>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
