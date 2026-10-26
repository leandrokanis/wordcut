import { useRoutes, type RouteObject } from "react-router-dom";

import { SermonList } from "../features/sermons/SermonList";
import { SettingsPage } from "../features/settings/SettingsPage";
import { Layout } from "./Layout";
import { LevelPlaceholder } from "./LevelPlaceholder";
import { Shell } from "./Shell";

export const routes: RouteObject[] = [
  {
    element: <Shell />,
    children: [
      {
        element: <Layout />,
        children: [
          { path: "/", element: <SermonList /> },
          {
            path: "/sermons/:id",
            element: <LevelPlaceholder notFound="Pregação não encontrada." />,
          },
          { path: "/cuts/:id", element: <LevelPlaceholder notFound="Corte não encontrado." /> },
        ],
      },
      { path: "/settings", element: <SettingsPage /> },
    ],
  },
];

export function AppRoutes() {
  return useRoutes(routes);
}
