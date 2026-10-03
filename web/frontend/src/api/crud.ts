// Shared CRUD API helper for all frontend pages.
// Handles array and object-wrapped responses, pagination, loading states, and errors.

export interface PaginatedResponse<T> {
  items?: T[];
  data?: T[];
  total?: number;
  page?: number;
  limit?: number;
}

export interface ListResult<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}

export interface CrudOptions {
  baseUrl?: string;
  headers?: Record<string, string>;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function unwrap<T>(body: T[] | PaginatedResponse<T>): T[] {
  if (Array.isArray(body)) return body;
  return body.items ?? body.data ?? [];
}

function extractTotal<T>(body: T[] | PaginatedResponse<T>, fallback: number): number {
  if (Array.isArray(body)) return fallback;
  return body.total ?? fallback;
}

export class CrudApi<T extends { id: string | number }> {
  private baseUrl: string;
  private defaultHeaders: Record<string, string>;

  constructor(
    private endpoint: string,
    options: CrudOptions = {},
  ) {
    this.baseUrl = options.baseUrl ?? '/api';
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
  }

  private url(path = '', params?: Record<string, string | number>): string {
    const qs = params
      ? '?' + new URLSearchParams(
          Object.entries(params).map(([k, v]) => [k, String(v)]),
        ).toString()
      : '';
    return `${this.baseUrl}/${this.endpoint}${path}${qs}`;
  }

  private async request<R>(
    input: string,
    init?: RequestInit,
  ): Promise<R> {
    let res: Response;
    try {
      res = await fetch(input, {
        ...init,
        headers: { ...this.defaultHeaders, ...init?.headers },
      });
    } catch {
      throw new ApiError('Network error – check your connection', 0);
    }

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new ApiError(text || res.statusText, res.status);
    }

    if (res.status === 204) return undefined as R;
    return res.json() as Promise<R>;
  }

  async list(params?: {
    page?: number;
    limit?: number;
    [key: string]: string | number | undefined;
  }): Promise<ListResult<T>> {
    const { page = 1, limit = 20, ...rest } = params ?? {};
    const body = await this.request<T[] | PaginatedResponse<T>>(
      this.url('', { page, limit, ...rest }),
    );
    const items = unwrap(body);
    return {
      items,
      total: extractTotal(body, items.length),
      page,
      limit,
    };
  }

  async get(id: string | number): Promise<T> {
    return this.request<T>(this.url(`/${encodeURIComponent(String(id))}`));
  }

  async create(data: Omit<T, 'id'> & Partial<Pick<T, 'id'>>): Promise<T> {
    return this.request<T>(this.url(), {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async update(
    id: string | number,
    data: Partial<T>,
  ): Promise<T> {
    return this.request<T>(this.url(`/${encodeURIComponent(String(id))}`), {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async delete(id: string | number): Promise<void> {
    await this.request<void>(this.url(`/${encodeURIComponent(String(id))}`), {
      method: 'DELETE',
    });
  }
}

// Convenience factory for quick instantiation.
export function crud<T extends { id: string | number }>(
  endpoint: string,
  options?: CrudOptions,
): CrudApi<T> {
  return new CrudApi<T>(endpoint, options);
}
