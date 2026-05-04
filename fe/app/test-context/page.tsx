'use client';

import { Chat } from '@/components/chat';
import { useState } from 'react';

export default function TestContextPage() {
  const [tenantId, setTenantId] = useState('1001');
  const [projectId, setProjectId] = useState('5001');
  const [taskId, setTaskId] = useState('');

  const contextMetadata = {
    tenant_id: parseInt(tenantId, 10),
    project_id: parseInt(projectId, 10),
    ...(taskId && { task_id: parseInt(taskId, 10) }),
  };

  return (
    <div className="flex h-screen flex-col">
      <header className="border-b p-4">
        <h1 className="text-xl font-semibold mb-4">
          Test Context Metadata
        </h1>

        <div className="flex gap-4">
          <div>
            <label className="block text-sm mb-1">Tenant ID</label>
            <input
              type="number"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              className="border rounded px-2 py-1 w-24"
            />
          </div>

          <div>
            <label className="block text-sm mb-1">Project ID</label>
            <input
              type="number"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className="border rounded px-2 py-1 w-24"
            />
          </div>

          <div>
            <label className="block text-sm mb-1">Task ID (optional)</label>
            <input
              type="number"
              value={taskId}
              onChange={(e) => setTaskId(e.target.value)}
              placeholder="100"
              className="border rounded px-2 py-1 w-24"
            />
          </div>
        </div>

        <div className="mt-2 text-sm text-gray-600">
          <strong>Current metadata:</strong> {JSON.stringify(contextMetadata)}
        </div>

        <div className="mt-2 text-xs text-gray-500">
          <strong>Test scenarios:</strong>
          <ul className="list-disc ml-5 mt-1">
            <li>Tenant 1001, Project 5001: Champions League 2024-25 semifinals</li>
            <li>Tenant 1001, Project 5001, Task 100: Tactical analysis</li>
            <li>Tenant 1001, Project 5002: Champions League 2023-24 semifinals</li>
            <li>Tenant 1003, Project 6001: Philosophy books</li>
          </ul>
        </div>
      </header>

      <Chat
        config={{
          metadata: contextMetadata,
        }}
      />
    </div>
  );
}
