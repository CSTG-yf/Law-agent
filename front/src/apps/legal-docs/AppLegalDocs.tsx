import * as React from 'react';

import { Box, Container, Stack, Typography } from '@mui/joy';

import { LegalDocumentsPanel } from '~/modules/legal-docs';

export function AppLegalDocs() {
  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <Container
        maxWidth="xl"
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          py: 2,
        }}
      >
        <Stack spacing={2} sx={{ height: '100%', overflow: 'hidden' }}>
          <Box>
            <Typography level="h2" sx={{ mb: 1 }}>
              法律文档管理
            </Typography>
            <Typography level="body-sm" color="neutral">
              上传、管理和搜索法律文档，支持在 AI 对话中进行知识提取
            </Typography>
          </Box>

          <Box
            sx={{
              flex: 1,
              overflow: 'hidden',
              borderRadius: 'md',
              border: '1px solid',
              borderColor: 'divider',
              backgroundColor: 'background.surface',
            }}
          >
            <LegalDocumentsPanel />
          </Box>
        </Stack>
      </Container>
    </Box>
  );
}
