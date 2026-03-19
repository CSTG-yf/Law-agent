import * as React from 'react';

import { Drawer } from '@mui/joy';

import { useLegalDocumentsStore } from './store-legal-docs';
import { LegalDocumentsPanel } from './LegalDocumentsPanel';

interface LegalDocumentsMobileDrawerProps {
  onDocumentSelect?: (document: any) => void;
}

export function LegalDocumentsMobileDrawer({ onDocumentSelect }: LegalDocumentsMobileDrawerProps) {
  const { isPanelOpen, togglePanel } = useLegalDocumentsStore();

  return (
    <Drawer
      id="legal-docs-mobile-drawer"
      anchor="right"
      open={isPanelOpen}
      onClose={togglePanel}
      sx={{
        '--Drawer-horizontalSize': 'clamp(280px, 80%, 100%)',
        '--Drawer-transitionDuration': '0.3s',
      }}
      slotProps={{
        content: {
          sx: {
            backgroundColor: 'background.surface',
            borderTopLeftRadius: 'var(--AGI-Optima-Radius)',
            borderBottomLeftRadius: 'var(--AGI-Optima-Radius)',
          },
        },
      }}
    >
      <LegalDocumentsPanel onDocumentSelect={onDocumentSelect} />
    </Drawer>
  );
}
