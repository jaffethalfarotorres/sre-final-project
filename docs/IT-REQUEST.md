# IT request for the SRE Academy lab

This page has two parts:

1. **A request you can copy and paste** into IBM's IT help process (or the laptop admin process of your site). It lists exactly what the lab needs.
2. **A decision checklist for the academy.** Some choices belong to the academy, not to each student. Decide them once, before the course, so every student asks IT for the same thing.

Run the preflight first. It only reads, needs no admin rights and shows what is missing on your laptop:

```
Windows (PowerShell):  python scripts\preflight.py
Mac:                   python3 scripts/preflight.py
```

No git yet? On the GitHub page of the repository click **Code > Download ZIP**, unzip it, open a terminal in that folder and run the same line. Attach its output to the request. If `python` itself is missing, say so in the request: Python is on the list below.

---

## 1. Request template (copy and paste)

> **Subject:** Software and network access for the SRE Academy lab (training)
>
> Hello,
>
> I am a student in the SRE Academy (IBM Costa Rica). The course lab runs a small Kubernetes cluster **on my own laptop only** (Minikube). Nothing connects to IBM systems or to client data. I need the following for the course dates: `<start date>` to `<end date>`.
>
> **1. Install rights.** One of these:
> - temporary local administrator rights for the course period, **or**
> - installation of the packages below by IT.
>
> **2. Software** (Windows package IDs for `winget`; Mac uses Homebrew):
>
> | Purpose | Windows (`winget install -e --id ...`) | Mac (`brew install ...`) |
> | --- | --- | --- |
> | Container engine (one of them, see note A) | `SUSE.RancherDesktop` or `Docker.DockerDesktop` | `colima docker` |
> | Linux layer for the container engine | WSL2 (Windows feature, turned on by the engine installer; needs a restart) | not needed |
> | Linux for Ansible (lab Part 5, M10) | WSL2 with the Ubuntu distribution: Ansible does not run in Windows PowerShell | not needed |
> | Local Kubernetes | `Kubernetes.minikube`, `Kubernetes.kubectl` | `minikube kubectl` |
> | Infrastructure as code (lab Part 5, M11) | `Hashicorp.Terraform` | `hashicorp/tap/terraform` (after `brew tap hashicorp/tap`) |
> | Packaging (optional, one module) | `Helm.Helm` | `helm` |
> | Source control | `Git.Git`, `GitHub.cli` | `git gh` |
> | Python 3.12 (user scope is enough) | `Python.Python.3.12 --scope user` | `python@3.12` |
> | Mac only: package manager | not needed | Homebrew from https://brew.sh |
>
> **Note A, container engine.** Docker Desktop needs a paid subscription in large companies. If IBM does not provide me a Docker Desktop licence, please install **Rancher Desktop** (free, open source) instead. On a Mac the lab uses Colima (free, open source).
>
> **3. PowerShell scripts** (Windows). The lab runs its own scripts with `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\<name>.ps1`. This works unless a Group Policy forces `AllSigned` or `Restricted`. If it does on my laptop, please allow these scripts or tell me the approved way to run them.
>
> **4. Outbound HTTPS (port 443)** to these sites, on and off the VPN:
>
> | Site | Why |
> | --- | --- |
> | `github.com`, `api.github.com`, `codeload.github.com`, `objects.githubusercontent.com`, `raw.githubusercontent.com` | the course repository, my fork, GitHub Actions results, tool downloads |
> | `ghcr.io` | container images (GitHub registry) |
> | `registry-1.docker.io`, `auth.docker.io`, `production.cloudflare.docker.com` (Docker Hub) | container images: Prometheus, Grafana, Loki, Jaeger, Python base image |
> | `quay.io` | container images for optional modules (AWX operator, Argo) |
> | `registry.k8s.io`, `gcr.io` | Kubernetes and Minikube images |
> | `pypi.org`, `files.pythonhosted.org` | Python packages for the lab tests and for Ansible |
> | `galaxy.ansible.com` | the Ansible `kubernetes.core` collection (Part 5) |
> | `releases.hashicorp.com`, `registry.terraform.io` | Terraform and its Kubernetes provider (Part 5) |
> | `prometheus-community.github.io`, `litmuschaos.github.io` | Helm charts for optional modules |
> | `ntfy.sh` | test alerts sent to my phone (no account, no IBM data) |
> | `bob.ibm.com` | IBM Bob, the AI assistant used in the course (if not already approved) |
>
> **5. Hardware check.** The lab needs 8 GB of RAM (16 GB recommended), 20 GB of free disk (25 GB recommended) and 2 CPU cores (4 recommended). The output of the course's read-only check script is attached.
>
> Thank you.

---

## 2. Decision checklist for the academy

Decide these before the course starts, and write the answers into the course welcome mail. Then every student sends the same request, and IT sees one consistent pattern.

| # | Decision | Options | Who decides | Decided? |
| --- | --- | --- | --- | --- |
| 1 | Container engine on Windows | Rancher Desktop (free) or Docker Desktop (licence needed). The scripts work with both. | Academy lead, with IT | [ ] |
| 2 | How students get install rights | Temporary admin rights per student, or IT installs the package list for the whole cohort | Academy lead and IT | [ ] |
| 3 | IBM Bob entitlement | Confirm every student has Bob access before week 1. Without Bob the lab still works by hand ([GUIDE.md](GUIDE.md)). | Academy lead | [ ] |
| 4 | Network | Confirm the sites in section 4 work on the IBM VPN, or tell students to install off the VPN where policy allows | IT | [ ] |
| 5 | PowerShell policy | Confirm no Group Policy blocks `-ExecutionPolicy Bypass`, or give an approved way. The fallback is the WSL2 and Ubuntu path in [GUIDE.md](GUIDE.md#windows-by-hand-wsl2-and-ubuntu). | IT | [ ] |
| 6 | 8 GB laptops | Accept them for the core path only (add-ons as instructor demos), or provide loaner or lab machines | Academy lead | [ ] |
| 7 | Phone alerts | ntfy.sh is allowed (no account, the topic name is the only secret). IBM Slack and IBM mail are **not** used by the lab. | Academy lead | [ ] |
| 8 | Pre-course week | One week before class: students run the preflight, send the IT request, and install the tools. A drop-in hour for problems. | Academy lead | [ ] |

### Suggested timeline

| When | What |
| --- | --- |
| 3 weeks before | Academy decides items 1-8 and sends the welcome mail with this page. |
| 2 weeks before | Students run the preflight and send the IT request with its output. |
| 1 week before | Students install the tools (by hand with [GUIDE.md](GUIDE.md), or with IBM Bob and [BOB-QUICKSTART.md](BOB-QUICKSTART.md)) and run the preflight again. Drop-in hour for FAIL lines. |
| Day 1 | Every preflight shows no FAIL. Part 1 of the lab starts with a working laptop. |

## What this page does not promise

- It does not replace IBM policy. If IT says no to an item, follow IT. The lab has a fallback for most items (8 GB profile, WSL2 path, instructor demos).
- The site list comes from the files in this repository (container images, scripts and install guides). A tool update can add a new download host. If something new is blocked, the error message names the host: add it to the request.
