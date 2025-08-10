/**
 * API Client for Crypto-0DTE System
 * 
 * Centralized API client with error handling, retries, and request/response interceptors.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class APIError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

class APIClient {
  constructor(baseURL = API_BASE_URL) {
    this.baseURL = baseURL;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
    this.requestInterceptors = [];
    this.responseInterceptors = [];
  }

  // Add request interceptor
  addRequestInterceptor(interceptor) {
    this.requestInterceptors.push(interceptor);
  }

  // Add response interceptor
  addResponseInterceptor(interceptor) {
    this.responseInterceptors.push(interceptor);
  }

  // Apply request interceptors
  async applyRequestInterceptors(config) {
    let modifiedConfig = { ...config };
    for (const interceptor of this.requestInterceptors) {
      modifiedConfig = await interceptor(modifiedConfig);
    }
    return modifiedConfig;
  }

  // Apply response interceptors
  async applyResponseInterceptors(response) {
    let modifiedResponse = response;
    for (const interceptor of this.responseInterceptors) {
      modifiedResponse = await interceptor(modifiedResponse);
    }
    return modifiedResponse;
  }

  // Make HTTP request with retries
  async request(endpoint, options = {}) {
    const {
      method = 'GET',
      data,
      params,
      headers = {},
      timeout = 30000,
      retries = 3,
      retryDelay = 1000,
      ...otherOptions
    } = options;

    // Build URL
    let url = `${this.baseURL}${endpoint}`;
    if (params) {
      const searchParams = new URLSearchParams(params);
      url += `?${searchParams.toString()}`;
    }

    // Prepare request config
    let config = {
      method,
      headers: { ...this.defaultHeaders, ...headers },
      ...otherOptions
    };

    // Add body for POST/PUT/PATCH requests
    if (data && ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase())) {
      config.body = JSON.stringify(data);
    }

    // Apply request interceptors
    config = await this.applyRequestInterceptors(config);

    // Retry logic
    let lastError;
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        config.signal = controller.signal;

        // Make request
        const response = await fetch(url, config);
        clearTimeout(timeoutId);

        // Apply response interceptors
        const interceptedResponse = await this.applyResponseInterceptors(response);

        // Handle response
        if (!interceptedResponse.ok) {
          const errorData = await interceptedResponse.json().catch(() => ({}));
          throw new APIError(
            errorData.message || `HTTP ${interceptedResponse.status}`,
            interceptedResponse.status,
            errorData
          );
        }

        // Parse response
        const contentType = interceptedResponse.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          return await interceptedResponse.json();
        } else {
          return await interceptedResponse.text();
        }

      } catch (error) {
        lastError = error;

        // Don't retry on certain errors
        if (error.name === 'AbortError') {
          throw new APIError('Request timeout', 408, { timeout });
        }

        if (error instanceof APIError && error.status < 500) {
          // Client errors (4xx) - don't retry
          throw error;
        }

        // Retry on network errors and 5xx errors
        if (attempt < retries) {
          const delay = retryDelay * Math.pow(2, attempt); // Exponential backoff
          console.warn(`Request failed, retrying in ${delay}ms... (${attempt + 1}/${retries})`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    throw lastError;
  }

  // Convenience methods
  async get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  async post(endpoint, data, options = {}) {
    return this.request(endpoint, { ...options, method: 'POST', data });
  }

  async put(endpoint, data, options = {}) {
    return this.request(endpoint, { ...options, method: 'PUT', data });
  }

  async patch(endpoint, data, options = {}) {
    return this.request(endpoint, { ...options, method: 'PATCH', data });
  }

  async delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }

  // API-specific methods
  async getMarketData(symbol, timeframe = '1h', limit = 100) {
    return this.get('/api/v1/market-data/ohlcv', {
      params: { symbol, timeframe, limit }
    });
  }

  async getPortfolioStatus() {
    return this.get('/api/v1/portfolio/status');
  }

  async getSignals(limit = 10) {
    return this.get('/api/v1/signals/recent', {
      params: { limit }
    });
  }

  async getTrades(limit = 10) {
    return this.get('/api/v1/trading/recent', {
      params: { limit }
    });
  }

  async getEnvironmentStatus() {
    return this.get('/api/v1/autonomous/environment');
  }

  async switchEnvironment(environment) {
    return this.post('/api/v1/autonomous/environment', { environment });
  }

  async emergencyStop() {
    return this.post('/api/v1/autonomous/emergency-stop');
  }

  async getHealthStatus() {
    return this.get('/api/v1/health');
  }

  async getMetrics() {
    return this.get('/api/v1/metrics');
  }

  async getOrdersJournal(params = {}) {
    return this.get('/api/v1/trading/orders', { params });
  }

  async getRealTimeMetrics() {
    return this.get('/api/v1/metrics/realtime');
  }
}

// Create singleton instance
const apiClient = new APIClient();

// Add default request interceptor for logging
apiClient.addRequestInterceptor(async (config) => {
  console.log(`API Request: ${config.method} ${config.url}`);
  return config;
});

// Add default response interceptor for logging
apiClient.addResponseInterceptor(async (response) => {
  console.log(`API Response: ${response.status} ${response.url}`);
  return response;
});

export default apiClient;
export { APIError };

