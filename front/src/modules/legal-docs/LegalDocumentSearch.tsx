import * as React from 'react';

import { Box, Chip, Input, Option, Select, Stack, Typography } from '@mui/joy';
import SearchIcon from '@mui/icons-material/Search';
import FilterListIcon from '@mui/icons-material/FilterList';

import { useLegalDocumentsStore, getDocumentCategories } from './store-legal-docs';

interface LegalDocumentSearchProps {
  onDocumentSelect?: (documentId: string) => void;
}

export function LegalDocumentSearch({ onDocumentSelect }: LegalDocumentSearchProps) {
  const { searchQuery, setSearchQuery, selectedCategory, setSelectedCategory, documents } = useLegalDocumentsStore();

  const categories = React.useMemo(() => getDocumentCategories(documents), [documents]);

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value);
  };

  const handleCategoryChange = (_: any, value: string | null) => {
    setSelectedCategory(value);
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedCategory(null);
  };

  const hasActiveFilters = searchQuery || selectedCategory;

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={1} alignItems="center">
        <FilterListIcon color="primary" />
        <Typography level="title-md">文档搜索</Typography>
      </Stack>

      <Box sx={{ position: 'relative' }}>
        <Input
          placeholder="搜索文档名称、内容或标签..."
          value={searchQuery}
          onChange={handleSearchChange}
          startDecorator={<SearchIcon />}
          fullWidth
        />
      </Box>

      <Stack direction="row" spacing={1} alignItems="center">
        <Select
          placeholder="选择分类"
          value={selectedCategory}
          onChange={handleCategoryChange}
          sx={{ minWidth: 150 }}
        >
          <Option value={null}>全部分类</Option>
          {categories.map((category) => (
            <Option key={category} value={category}>
              {category}
            </Option>
          ))}
        </Select>

        {hasActiveFilters && (
          <Chip
            variant="soft"
            color="neutral"
            onClick={clearFilters}
            sx={{ cursor: 'pointer' }}
          >
            清除筛选
          </Chip>
        )}
      </Stack>

      {hasActiveFilters && (
        <Stack direction="row" spacing={1} flexWrap="wrap">
          {searchQuery && (
            <Chip
              variant="outlined"
              color="primary"
              endDecorator={
                <Box
                  component="span"
                  onClick={() => setSearchQuery('')}
                  sx={{ cursor: 'pointer' }}
                >
                  ×
                </Box>
              }
            >
              搜索: {searchQuery}
            </Chip>
          )}
          {selectedCategory && (
            <Chip
              variant="outlined"
              color="primary"
              endDecorator={
                <Box
                  component="span"
                  onClick={() => setSelectedCategory(null)}
                  sx={{ cursor: 'pointer' }}
                >
                  ×
                </Box>
              }
            >
              分类: {selectedCategory}
            </Chip>
          )}
        </Stack>
      )}
    </Stack>
  );
}
