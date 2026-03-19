import * as React from 'react';

import { Box, Button, Card, Chip, Divider, IconButton, List, ListItem, ListItemButton, ListItemContent, ListItemDecorator, Stack, Typography, useColorScheme } from '@mui/joy';
import AddIcon from '@mui/icons-material/Add';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DeleteIcon from '@mui/icons-material/Delete';
import DescriptionIcon from '@mui/icons-material/Description';
import FolderIcon from '@mui/icons-material/Folder';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import VisibilityIcon from '@mui/icons-material/Visibility';

import type { LegalDocument } from './store-legal-docs';
import { useLegalDocumentsStore, getFilteredDocuments } from './store-legal-docs';
import { LegalDocumentSearch } from './LegalDocumentSearch';
import { LegalDocumentUpload } from './LegalDocumentUpload';

interface LegalDocumentsPanelProps {
  onDocumentSelect?: (document: LegalDocument) => void;
  compact?: boolean;
}

export function LegalDocumentsPanel({ onDocumentSelect, compact = false }: LegalDocumentsPanelProps) {
  const { documents, selectedDocumentId, selectDocument, removeDocument } = useLegalDocumentsStore();
  const [uploadModalOpen, setUploadModalOpen] = React.useState(false);
  const [viewDocumentId, setViewDocumentId] = React.useState<string | null>(null);

  const filteredDocuments = React.useMemo(() => getFilteredDocuments(useLegalDocumentsStore.getState()), [documents]);

  const { mode } = useColorScheme();

  const handleDocumentClick = (document: LegalDocument) => {
    selectDocument(document.id);
    onDocumentSelect?.(document);
  };

  const handleViewDocument = (e: React.MouseEvent, documentId: string) => {
    e.stopPropagation();
    setViewDocumentId(documentId);
  };

  const handleDeleteDocument = (e: React.MouseEvent, documentId: string) => {
    e.stopPropagation();
    if (confirm('确定要删除这个文档吗？')) {
      removeDocument(documentId);
      if (viewDocumentId === documentId) {
        setViewDocumentId(null);
      }
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (timestamp: number): string => {
    return new Date(timestamp).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  };

  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'pdf':
        return <DescriptionIcon />;
      case 'doc':
      case 'docx':
        return <InsertDriveFileIcon />;
      case 'txt':
        return <DescriptionIcon />;
      default:
        return <FolderIcon />;
    }
  };

  const selectedDocument = documents.find((doc) => doc.id === selectedDocumentId);
  const viewDocument = documents.find((doc) => doc.id === viewDocumentId);

  return (
    <Stack spacing={2} sx={{ height: '100%' }}>
      <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
        <Typography level="title-lg">法律文档库</Typography>
        <Button
          size="sm"
          variant="solid"
          startDecorator={<AddIcon />}
          onClick={() => setUploadModalOpen(true)}
        >
          上传文档
        </Button>
      </Stack>

      <Divider />

      <LegalDocumentSearch />

      <Divider />

      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {filteredDocuments.length === 0 ? (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'neutral.400',
            }}
          >
            <FolderIcon sx={{ fontSize: 64, mb: 2 }} />
            <Typography level="body-sm">暂无文档</Typography>
            <Typography level="body-xs" color="neutral.400">
              点击"上传文档"开始添加
            </Typography>
          </Box>
        ) : (
          <List>
            {filteredDocuments.map((document) => (
              <ListItem key={document.id}>
                <ListItemButton
                  selected={selectedDocumentId === document.id}
                  onClick={() => handleDocumentClick(document)}
                  sx={{
                    borderRadius: 'md',
                    mb: 1,
                  }}
                >
                  <ListItemDecorator>{getFileIcon(document.name)}</ListItemDecorator>
                  <ListItemContent>
                    <Stack spacing={0.5}>
                      <Typography level="body-sm" fontWeight={selectedDocumentId === document.id ? 'bold' : 'normal'}>
                        {document.name}
                      </Typography>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography level="body-xs" color="neutral.400">
                          {formatFileSize(document.size)}
                        </Typography>
                        <Typography level="body-xs" color="neutral.400">
                          ·
                        </Typography>
                        <Typography level="body-xs" color="neutral.400">
                          {formatDate(document.uploadedAt)}
                        </Typography>
                      </Stack>
                      {document.category && (
                        <Chip size="sm" variant="soft" sx={{ mt: 0.5 }}>
                          {document.category}
                        </Chip>
                      )}
                      {document.tags && document.tags.length > 0 && (
                        <Stack direction="row" spacing={0.5} flexWrap="wrap" sx={{ mt: 0.5 }}>
                          {document.tags.slice(0, 3).map((tag, index) => (
                            <Chip key={index} size="sm" variant="outlined" sx={{ fontSize: '0.7rem' }}>
                              {tag}
                            </Chip>
                          ))}
                          {document.tags.length > 3 && (
                            <Chip size="sm" variant="outlined" sx={{ fontSize: '0.7rem' }}>
                              +{document.tags.length - 3}
                            </Chip>
                          )}
                        </Stack>
                      )}
                    </Stack>
                  </ListItemContent>
                  <Stack direction="row" spacing={0.5}>
                    <IconButton
                      size="sm"
                      onClick={(e) => handleViewDocument(e, document.id)}
                    >
                      <VisibilityIcon />
                    </IconButton>
                    <IconButton
                      size="sm"
                      color="danger"
                      onClick={(e) => handleDeleteDocument(e, document.id)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Stack>
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        )}
      </Box>

      {viewDocument && (
        <Card
          variant="outlined"
          sx={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            maxWidth: '80vw',
            maxHeight: '80vh',
            zIndex: 9999,
            overflow: 'auto',
          }}
        >
          <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between" mb={2}>
            <Typography level="title-md">{viewDocument.name}</Typography>
            <IconButton
              size="sm"
              onClick={() => setViewDocumentId(null)}
            >
              <CheckCircleIcon />
            </IconButton>
          </Stack>
          <Divider sx={{ mb: 2 }} />
          <Box
            sx={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              maxHeight: '60vh',
              overflow: 'auto',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              lineHeight: 1.6,
            }}
          >
            {viewDocument.content}
          </Box>
        </Card>
      )}

      <LegalDocumentUpload
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
      />
    </Stack>
  );
}
