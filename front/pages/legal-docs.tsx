import * as React from 'react';

import { AppLegalDocs } from '../src/apps/legal-docs/AppLegalDocs';

import { withLayout } from '~/common/layout/withLayout';


export default function LegalDocsPage() {
  return withLayout({ type: 'optima' }, <AppLegalDocs />);
}
