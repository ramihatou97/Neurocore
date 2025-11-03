/**
 * Analytics Page
 * Placeholder - Original version requires @mui/material
 */

import { Card } from '../components';

const Analytics = () => {
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Analytics
          </h1>
          <p className="text-gray-600">
            System analytics and metrics dashboard
          </p>
        </div>

        <Card className="text-center py-12">
          <div className="text-6xl mb-4">📊</div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Analytics Dashboard
          </h3>
          <p className="text-gray-600 mb-4">
            The analytics dashboard is currently undergoing updates.
          </p>
          <p className="text-sm text-gray-500">
            This page will display comprehensive system metrics, user activity, and performance analytics.
          </p>
        </Card>
      </div>
    </div>
  );
};

export default Analytics;
