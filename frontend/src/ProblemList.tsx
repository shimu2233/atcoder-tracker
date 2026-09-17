import BookmarkAddOutlinedIcon from "@mui/icons-material/BookmarkAddOutlined";
import BookmarkRemoveRoundedIcon from "@mui/icons-material/BookmarkRemoveRounded";
import OpenInNewRoundedIcon from "@mui/icons-material/OpenInNewRounded";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
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
import { useMemo, useState } from "react";
import type { ProblemItem, ProblemListData } from "./types";

const statusColor = (status: ProblemItem["status"]) => {
  if (status === "AC済み") return "success";
  if (status === "未AC") return "warning";
  return "default";
};

export function ProblemList({ data, csrfToken }: { data: ProblemListData; csrfToken: string }) {
  const [section, setSection] = useState(data.sections[0]?.name ?? "");
  const [sections, setSections] = useState(data.sections);
  const visibleItems = useMemo(
    () => sections.find((candidate) => candidate.name === section)?.items ?? [],
    [section, sections]
  );
  const total = sections.reduce((sum, candidate) => sum + candidate.items.length, 0);

  const toggleDoLater = async (item: ProblemItem) => {
    const response = await fetch(item.toggle_url, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken },
      credentials: "same-origin"
    });
    if (!response.ok) return;
    setSections((current) => current.map((candidate) => ({
      ...candidate,
      items: candidate.items
        .map((row) => row.problem_id === item.problem_id
          ? { ...row, is_do_later: !row.is_do_later }
          : row)
        .filter((row) => !(data.remove_when_unbookmarked && row.problem_id === item.problem_id))
    })));
  };

  if (!total) return <Alert severity="info">{data.empty_message}</Alert>;

  return (
    <Card>
      {sections.length > 1 && (
        <Tabs
          value={section}
          onChange={(_, value) => setSection(value)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ px: 2, borderBottom: 1, borderColor: "divider" }}
        >
          {sections.map((candidate) => (
            <Tab key={candidate.name} value={candidate.name} label={candidate.name} />
          ))}
        </Tabs>
      )}
      <CardContent>
        <TableContainer sx={{ overflowX: "auto" }}>
          <Table size="small" aria-label="問題一覧">
            <TableHead>
              <TableRow>
                <TableCell>問題</TableCell>
                <TableCell>問題名</TableCell>
                <TableCell>分野</TableCell>
                <TableCell align="right">難易度</TableCell>
                <TableCell>状態</TableCell>
                <TableCell align="center">後でやる</TableCell>
                <TableCell align="center">開く</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {visibleItems.map((item) => (
                <TableRow key={item.problem_id} hover>
                  <TableCell sx={{ whiteSpace: "nowrap", fontWeight: 700 }}>
                    {item.problem_index || "-"}
                  </TableCell>
                  <TableCell>{item.name}</TableCell>
                  <TableCell>{item.category || "-"}</TableCell>
                  <TableCell align="right">{item.difficulty ?? "-"}</TableCell>
                  <TableCell>
                    <Chip size="small" color={statusColor(item.status)} label={item.status} />
                  </TableCell>
                  <TableCell align="center" sx={{ whiteSpace: "nowrap" }}>
                    <Button
                      size="small"
                      onClick={() => toggleDoLater(item)}
                      startIcon={item.is_do_later
                        ? <BookmarkRemoveRoundedIcon />
                        : <BookmarkAddOutlinedIcon />}
                    >
                      {item.is_do_later ? "解除" : "後でやる"}
                    </Button>
                  </TableCell>
                  <TableCell align="center" sx={{ whiteSpace: "nowrap" }}>
                    <Button
                      size="small"
                      component="a"
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      endIcon={<OpenInNewRoundedIcon />}
                    >
                      開く
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
}
