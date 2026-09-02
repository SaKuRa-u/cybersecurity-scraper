import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import DataBrowser from './components/DataBrowser'
import Analytics from './components/Analytics'
import SessionHistory from './components/SessionHistory'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex space-x-8">
                <Link 
                  to="/" 
                  className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent hover:border-primary text-sm font-medium text-gray-900"
                >
                  Dashboard
                </Link>
                <Link 
                  to="/data" 
                  className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent hover:border-primary text-sm font-medium text-gray-900"
                >
                  Data Browser
                </Link>
                <Link 
                  to="/analytics" 
                  className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent hover:border-primary text-sm font-medium text-gray-900"
                >
                  Analytics
                </Link>
                <Link 
                  to="/sessions" 
                  className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent hover:border-primary text-sm font-medium text-gray-900"
                >
                  History
                </Link>
              </div>
              <div className="flex items-center">
                <h1 className="text-xl font-bold text-gray-900">
                  Cybersecurity Data Scraper
                </h1>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/data" element={<DataBrowser />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/sessions" element={<SessionHistory />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
