import { api, authenticated } from '.';

export const getTaskWaypoint = (projectId: string, taskId: string) =>
  authenticated(api).post(
    `/waypoint/task/${taskId}/?project_id=${projectId}&download=false`,
  );

export const getIndividualTask = (taskId: string) =>
  authenticated(api).get(`/tasks/${taskId}`);

export const getTaskAssetsInfo = (projectId: string, taskId: string) =>
  authenticated(api).get(`/projects/assets/${projectId}/${taskId}/`);
