import { Route, Routes } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import SearchResultsPage from './pages/SearchResultsPage';
import ProductResultPage from './pages/ProductResultPage';
import ScanResultPage from './pages/ScanResultPage';
import MyPagePage from './pages/MyPagePage';
import RoutinePage from './pages/RoutinePage';
import './App.css';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/search" element={<SearchResultsPage />} />
      <Route path="/product/:id" element={<ProductResultPage />} />
      <Route path="/scan-result" element={<ScanResultPage />} />
      <Route path="/mypage" element={<MyPagePage />} />
      <Route path="/routine" element={<RoutinePage />} />
    </Routes>
  );
}
