
export interface GoogleUser {
  email: string;
  name: string;
  picture: string;
  given_name: string;
  family_name: string;
  exp: number;
  iat: number;
  sub: string;
}

// Updated types for server-side OAuth
export interface UserResponse {
  id: string;
  email: string;
  name: string;
  given_name?: string;
  family_name?: string;
  picture?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthContextType {
  user: UserResponse | null;
  loading: boolean;
  login: () => void; // Updated to use server-side OAuth
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  setUser: React.Dispatch<React.SetStateAction<UserResponse | null>>;
}

// OAuth-specific types
export interface OAuthCallbackResponse {
  user: UserResponse;
  token: Token;
  message: string;
}

export interface OAuthStatusResponse {
  google_oauth_enabled: boolean;
  redirect_uri: string;
  available_flows: string[];
}

// Microsoft OAuth types
export interface MicrosoftUser {
  oid?: string;
  sub: string;
  tid?: string;
  email: string;
  name: string;
  given_name?: string;
  family_name?: string;
  exp?: number;
  iat?: number;
}

export interface MicrosoftOAuthStatusResponse {
  microsoft_oauth_enabled: boolean;
  redirect_uri: string;
  frontend_url: string;
  tenant_id: string;
  available_flows: string[];
}
