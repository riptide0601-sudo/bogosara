import { useNavigate } from 'react-router-dom';
import LoginView from '../components/LoginView';

/** 히어로의 LOGIN 링크(/login) 진입점. */
export default function LoginPage() {
  const navigate = useNavigate();

  return <LoginView onBack={() => navigate('/')} onSuccess={() => navigate('/mypage')} />;
}
