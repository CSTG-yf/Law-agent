import * as React from 'react';

import { Box, Button, Card, Chip, CircularProgress, Divider, IconButton, List, ListItem, ListItemContent, ListItemDecorator, Modal, ModalDialog, Option, Select, Stack, Textarea, Typography, useColorScheme } from '@mui/joy';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DeleteIcon from '@mui/icons-material/Delete';
import DescriptionIcon from '@mui/icons-material/Description';
import FolderIcon from '@mui/icons-material/Folder';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import CloseIcon from '@mui/icons-material/Close';

import type { LegalDocument } from './store-legal-docs';
import { useLegalDocumentsStore } from './store-legal-docs';

interface LegalDocumentUploadProps {
  open: boolean;
  onClose: () => void;
}

interface FileWithPreview extends File {
  preview?: string;
}

const LEGAL_FILE_TYPES = [
  '.pdf',
  '.doc',
  '.docx',
  '.txt',
  '.rtf',
  '.odt',
  '.html',
  '.htm',
];

const LEGAL_CATEGORIES = [
  '合同法',
  '刑法',
  '民法',
  '行政法',
  '经济法',
  '劳动法',
  '知识产权法',
  '国际法',
  '其他',
];

export function LegalDocumentUpload({ open, onClose }: LegalDocumentUploadProps) {
  const { addDocument } = useLegalDocumentsStore();

  const [files, setFiles] = React.useState<FileWithPreview[]>([]);
  const [uploading, setUploading] = React.useState(false);
  const [uploadProgress, setUploadProgress] = React.useState(0);
  const [category, setCategory] = React.useState<string>('其他');
  const [tags, setTags] = React.useState<string>('');
  const [dragActive, setDragActive] = React.useState(false);

  const { mode } = useColorScheme();

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = (fileList: FileList) => {
    const validFiles = Array.from(fileList).filter((file) => {
      const extension = '.' + file.name.split('.').pop()?.toLowerCase();
      return LEGAL_FILE_TYPES.includes(extension);
    });

    if (validFiles.length === 0) {
      alert('请上传有效的法律文档格式：' + LEGAL_FILE_TYPES.join(', '));
      return;
    }

    setFiles((prev) => [...prev, ...validFiles]);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const readFileContent = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        resolve(e.target?.result as string);
      };
      reader.onerror = (e) => {
        reject(e);
      };
      reader.readAsText(file);
    });
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      alert('请先选择文件');
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const content = await readFileContent(file);

        const document: LegalDocument = {
          id: `doc-${Date.now()}-${i}`,
          name: file.name,
          type: file.type || 'application/octet-stream',
          size: file.size,
          content: content,
          uploadedAt: Date.now(),
          category: category,
          tags: tags.split(',').map((tag) => tag.trim()).filter(Boolean),
        };

        addDocument(document);

        setUploadProgress(((i + 1) / files.length) * 100);
      }

      setFiles([]);
      setTags('');
      setCategory('其他');
      onClose();
    } catch (error) {
      console.error('上传失败:', error);
      alert('上传失败，请重试');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
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

  return (
    <Modal open={open} onClose={onClose}>
      <ModalDialog
        aria-labelledby="legal-doc-upload-title"
        sx={{
          maxWidth: '600px',
          width: '100%',
        }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography id="legal-doc-upload-title" level="h3">
            上传法律文档
          </Typography>
          <IconButton onClick={onClose} size="sm">
            <CloseIcon />
          </IconButton>
        </Stack>

        <Divider />

        <Stack spacing={3} sx={{ mt: 2 }}>
          <Box
            sx={{
              border: '2px dashed',
              borderColor: dragActive ? 'primary.500' : 'neutral.300',
              borderRadius: 'md',
              p: 4,
              textAlign: 'center',
              cursor: 'pointer',
              backgroundColor: dragActive ? 'primary.50' : 'background.surface',
              transition: 'all 0.2s',
              '&:hover': {
                borderColor: 'primary.400',
                backgroundColor: 'primary.50',
              },
            }}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              multiple
              accept={LEGAL_FILE_TYPES.join(',')}
              onChange={handleChange}
              style={{ display: 'none' }}
              id="legal-doc-input"
            />
            <label htmlFor="legal-doc-input">
              <Stack spacing={2} alignItems="center">
                <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.500' }} />
                <Typography level="body-sm" color="neutral">
                  拖拽文件到此处或点击选择文件
                </Typography>
                <Typography level="body-xs" color="neutral.400">
                  支持格式：{LEGAL_FILE_TYPES.join(', ')}
                </Typography>
              </Stack>
            </label>
          </Box>

          {files.length > 0 && (
            <Card variant="outlined">
              <Typography level="title-md" mb={2}>
                待上传文件 ({files.length})
              </Typography>
              <List>
                {files.map((file, index) => (
                  <ListItem key={index}>
                    <ListItemDecorator>{getFileIcon(file.name)}</ListItemDecorator>
                    <ListItemContent>
                      <Typography level="body-sm">{file.name}</Typography>
                      <Typography level="body-xs" color="neutral.400">
                        {formatFileSize(file.size)}
                      </Typography>
                    </ListItemContent>
                    <IconButton
                      size="sm"
                      color="danger"
                      onClick={() => removeFile(index)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </ListItem>
                ))}
              </List>
            </Card>
          )}

          <Stack spacing={2}>
            <Typography level="body-sm">文档分类</Typography>
            <Select
              value={category}
              onChange={(_, value) => setCategory(value as string)}
            >
              {LEGAL_CATEGORIES.map((cat) => (
                <Option key={cat} value={cat}>
                  {cat}
                </Option>
              ))}
            </Select>
          </Stack>

          <Stack spacing={2}>
            <Typography level="body-sm">标签（用逗号分隔）</Typography>
            <Textarea
              placeholder="例如：合同, 民法, 2024"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              minRows={2}
            />
          </Stack>

          {uploading && (
            <Stack spacing={1}>
              <Typography level="body-sm">上传中...</Typography>
              <CircularProgress value={uploadProgress} />
            </Stack>
          )}

          <Stack direction="row" spacing={2} justifyContent="flex-end">
            <Button variant="plain" onClick={onClose} disabled={uploading}>
              取消
            </Button>
            <Button
              onClick={handleUpload}
              disabled={files.length === 0 || uploading}
              startDecorator={<CloudUploadIcon />}
            >
              上传文档
            </Button>
          </Stack>
        </Stack>
      </ModalDialog>
    </Modal>
  );
}
