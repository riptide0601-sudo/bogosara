/** 백엔드 app/schemas/user.py 와 1:1 대응하는 응답 타입들. */

export interface UserRead {
  user_id: string;
  nickname: string;
  email: string;
  joined_at: string;
  notify_alerts: boolean;
}

export interface TokenRead {
  access_token: string;
  token_type: string;
  user: UserRead;
}

export interface SkinProfile {
  skin_types: string[];
  watched_ingredients: string[];
}

export interface SavedResultRead {
  product_id: string;
  product_name: string;
  brand: string | null;
  category: string | null;
  saved_at: string;
}
