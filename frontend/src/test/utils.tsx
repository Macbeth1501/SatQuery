import type { ReactElement } from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { SatQueryProvider } from '../context/SatQueryContext';

/**
 * Renders a component inside the providers the real app supplies.
 *
 * Several components call `useNavigate` or `useSatQuery`, so rendering them bare
 * throws before any assertion runs.
 */
export function renderWithProviders(
  ui: ReactElement,
  { route = '/', ...options }: RenderOptions & { route?: string } = {}
) {
  return render(ui, {
    wrapper: ({ children }) => (
      <MemoryRouter initialEntries={[route]}>
        <SatQueryProvider>{children}</SatQueryProvider>
      </MemoryRouter>
    ),
    ...options,
  });
}
