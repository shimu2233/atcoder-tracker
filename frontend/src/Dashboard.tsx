import {
  Alert,
  Box,
  Card,
  CardContent,
  LinearProgress,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from "@mui/material";
import type { DashboardData } from "./types";

export function Dashboard({ data }: { data: DashboardData }) {
  return (
    <Stack spacing={2}>
      {data.messages.map((message) => <Alert key={message}>{message}</Alert>)}

      <Card>
        <Tabs value="difficulty" sx={{ px: 2, borderBottom: 1, borderColor: "divider" }}>
          <Tab value="difficulty" label="難易度別" />
        </Tabs>
        <CardContent>
          <Stack spacing={3}>
            <Stack spacing={1.5}>
              {data.difficulty_stats.map((stat) => (
                <Stack key={stat.band} direction="row" spacing={2} alignItems="center">
                  <Box sx={{ width: 90, flexShrink: 0 }}>{stat.band}</Box>
                  <LinearProgress
                    variant="determinate"
                    value={stat.ac_rate}
                    sx={{ flex: 1, height: 12, borderRadius: 999 }}
                  />
                  <Box sx={{ width: 48, textAlign: "right" }}>{stat.ac_rate}%</Box>
                </Stack>
              ))}
            </Stack>
            <TableContainer sx={{ overflowX: "auto" }}>
              <Table size="small" aria-label="難易度別の成績">
                <TableHead>
                  <TableRow>
                    <TableCell>難易度帯</TableCell>
                    <TableCell align="right">提出</TableCell>
                    <TableCell align="right">AC</TableCell>
                    <TableCell align="right">AC率</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.difficulty_stats.map((stat) => (
                    <TableRow key={stat.band} hover>
                      <TableCell>{stat.band}</TableCell>
                      <TableCell align="right">{stat.total}</TableCell>
                      <TableCell align="right">{stat.ac}</TableCell>
                      <TableCell align="right">{stat.ac_rate}%</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
