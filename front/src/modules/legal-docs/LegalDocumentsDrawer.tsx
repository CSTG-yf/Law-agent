import * as React from 'react';
import { Panel } from 'react-resizable-panels';

import { Box, Sheet, styled } from '@mui/joy';

import { useLegalDocumentsStore } from './store-legal-docs';
import { LegalDocumentsPanel } from './LegalDocumentsPanel';

interface LegalDocumentsDrawerProps {
  onDocumentSelect?: (document: any) => void;
}

const LegalDocumentsDrawerSheet = styled(Sheet)(({ theme }) => ({
  width: '100%',
  height: '100dvh',
  backgroundColor: 'background.surface',
  borderLeft: '1px solid',
  borderLeftColor: theme.palette.divider,
  boxShadow: `0px 0px 6px 0 rgba(${theme.palette.neutral.darkChannel} / 0.12)`,
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
})) as typeof Sheet;

export function LegalDocumentsDrawer({ onDocumentSelect }: LegalDocumentsDrawerProps) {
  const { isPanelOpen } = useLegalDocumentsStore();

  if (!isPanelOpen) {
    return null;
  }

  return (
    <Panel defaultSize={25} minSize={20} maxSize={40} id="legal-docs-panel">
      <LegalDocumentsDrawerSheet>
        <Box sx={{ p: 2, height: '100%', overflow: 'hidden' }}>
          <LegalDocumentsPanel onDocumentSelect={onDocumentSelect} />
        </Box>
      </LegalDocumentsDrawerSheet>
    </Panel>
  );
}
