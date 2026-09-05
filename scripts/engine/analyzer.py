import re
from typing import Dict, List

# Allowed function calls in a linear scan that do NOT trigger "unknown complexity"
SAFE_FUNCTIONS = {
    'if', 'while', 'for', 'switch', 'catch',
    'size', 'length', 'empty', 'begin', 'end', 
    'push_back', 'pop_back', 'insert', 'erase', 'clear',
    'max', 'min', 'abs', 'swap', 'front', 'back', 'top', 'pop',
    'sizeof', 'printf', 'cout', 'cin', 'scanf'
}

class CodeAnalyzer:
    def __init__(self, code: str, tags: List[str]):
        self.code = code
        self.tags = [t.lower() for t in tags] if tags else []
        self.clean_code = re.sub(r'//.*|/\*.*?\*/|#.*', '', self.code, flags=re.DOTALL)
        self._analyze_patterns()

    def analyze(self) -> Dict[str, str]:
        return {
            "time_complexity": self._guess_time_complexity(),
            "space_complexity": self._guess_space_complexity(),
            "approach": self._guess_approach(),
            "intuition": self._guess_intuition(),
            "edge_cases": self._guess_edge_cases(),
            "lessons": self._guess_lessons()
        }

    def _analyze_patterns(self):
        # 1. Recursion
        self.has_recursion = False
        func_match = re.search(r'\bclass\s+Solution\s*\{.*?\b(\w+)\s*\(', self.clean_code, re.DOTALL)
        if func_match:
            func_name = func_match.group(1)
            calls = re.findall(rf'\b{func_name}\s*\(', self.clean_code[func_match.end():])
            if len(calls) > 0:
                self.has_recursion = True

        # 2. Loops
        self.loops = list(re.finditer(r'\b(for|while)\s*\(', self.clean_code))
        
        # 3. Sorting
        self.sort_matches = list(re.finditer(r'\b(std::)?sort\s*\(', self.clean_code))
        self.has_sort = len(self.sort_matches) > 0
        
        # 4. Binary Search
        bs_sig = bool(re.search(r'\b(low|left)\s*<=\s*(high|right)\b', self.clean_code) and 
                      re.search(r'\b(mid)\b', self.clean_code))
        bs_func = bool(re.search(r'\b(std::)?binary_search\s*\(', self.clean_code))
        self.has_binary_search = bs_sig or bs_func
        
        # Check what is inside loops
        self.sort_in_loop = False
        self.bs_in_loop = False
        self.unknown_call_in_loop = False
        
        for loop in self.loops:
            # Simple heuristic for loop body: from loop keyword to next closing brace matching scope, 
            # or just look at the chunk until next loop/end of function.
            # We'll just look ahead 200 chars or until next loop/sort.
            # More robust: find the `{` and matching `}`.
            # Without AST, we'll just check the substring between this loop and next loop/EOF.
            start_idx = loop.end()
            end_idx = len(self.clean_code)
            # Find first {
            bracket_idx = self.clean_code.find('{', start_idx, start_idx + 100)
            if bracket_idx != -1:
                # Naive matching
                count = 1
                curr = bracket_idx + 1
                while curr < len(self.clean_code) and count > 0:
                    if self.clean_code[curr] == '{': count += 1
                    elif self.clean_code[curr] == '}': count -= 1
                    curr += 1
                end_idx = curr if count == 0 else len(self.clean_code)
            else:
                # 1 liner, scan until ;
                semi_idx = self.clean_code.find(';', start_idx)
                if semi_idx != -1: end_idx = semi_idx + 1
            
            loop_body = self.clean_code[start_idx:end_idx]
            
            if re.search(r'\b(std::)?sort\s*\(', loop_body):
                self.sort_in_loop = True
                
            if re.search(r'\b(std::)?binary_search\s*\(', loop_body):
                self.bs_in_loop = True
                
            # Unknown calls
            calls = re.findall(r'\b([a-zA-Z_]\w*)\s*\(', loop_body)
            for call in calls:
                if call not in SAFE_FUNCTIONS and call != func_match.group(1) if func_match else True:
                    # Ignore vector/map method calls prefixed by '.' e.g. v.push_back
                    # Our regex already captured the method name.
                    if call not in SAFE_FUNCTIONS:
                        self.unknown_call_in_loop = True

        # 5. Nested Loops
        self.has_nested_loops = False
        if len(self.loops) > 1:
            for i, loop in enumerate(self.loops[:-1]):
                next_loop = self.loops[i+1]
                sub = self.clean_code[loop.end():next_loop.start()]
                if '{' not in sub or sub.count('{') > sub.count('}'):
                    self.has_nested_loops = True

        # 6. Data Structures & Space
        self.has_hash_map = bool(re.search(r'\b(std::)?(unordered_map|unordered_set)\b', self.clean_code))
        
        self.dynamic_space = False
        if self.has_hash_map:
            self.dynamic_space = True
        if re.search(r'\b(for|while)\b[^{]*\{[^{}]*\.push_back\s*\(', self.clean_code):
            self.dynamic_space = True
        if re.search(r'\bvector<.*?>\s+\w+\s*\(\s*[a-zA-Z_]\w*\s*\)', self.clean_code):
            self.dynamic_space = True
            
        # 7. Two Pointers / Sliding Window
        self.has_two_pointers = bool(re.search(r'\b(left|l|i)\s*=\s*0\b', self.clean_code) and 
                                     re.search(r'\b(right|r|j)\s*=\s*\w+\.size\(\)\s*-\s*1\b', self.clean_code))
        self.has_sliding_window = "sliding window" in self.tags

        self.is_linear_scan = (len(self.loops) == 1 and not self.has_nested_loops and 
                               not self.has_recursion and not self.sort_in_loop and 
                               not self.bs_in_loop and not self.unknown_call_in_loop)

    def _guess_time_complexity(self) -> str:
        if self.has_recursion:
            return "Analysis required"
        if self.has_nested_loops:
            return "Analysis required"
        if self.sort_in_loop or self.bs_in_loop or self.unknown_call_in_loop:
            return "Analysis required"
        
        if self.has_sort:
            return "O(N log N) - Sorting dominates"
        if self.has_binary_search and not self.has_nested_loops:
            return "O(log N) - Binary Search"
            
        if self.is_linear_scan:
            if self.has_hash_map:
                return "O(N) average - Linear scan with hash map operations"
            return "O(N) - Linear Scan"
            
        if len(self.loops) == 0 and not self.has_sort and not self.has_binary_search:
            return "Analysis required" 

        return "Analysis required"

    def _guess_space_complexity(self) -> str:
        if self.dynamic_space:
            if self.has_hash_map:
                return "O(N) - Hash map scales with input"
            return "O(N) - Dynamic data structures scale with input"
        
        if self.has_recursion:
            return "Analysis required"

        return "O(1) - Constant Space"

    def _guess_approach(self) -> str:
        approaches = []
        if self.has_two_pointers:
            approaches.append("Two Pointers to systematically eliminate possibilities")
        if self.has_sliding_window:
            approaches.append("Sliding Window to maintain a variable or fixed size subset")
        if self.has_hash_map:
            approaches.append("Hash Map / Frequency Counting for O(1) average lookups")
        if self.has_binary_search:
            approaches.append("Binary Search to halve the search space")
        if self.has_sort:
            approaches.append("Sorting to group elements or enable monotonicity")
        
        if approaches:
            return "Uses " + " and ".join(approaches) + "."
        if self.is_linear_scan:
            return "Uses a standard linear scan."
        return "Analysis required"

    def _guess_intuition(self) -> str:
        if self.has_two_pointers:
            return "By moving pointers from opposite ends or in tandem, we avoid checking every O(N^2) combination."
        if self.has_binary_search:
            return "The search space is monotonic, allowing us to find the target in logarithmic time rather than linear."
        if self.has_hash_map:
            return "Trading space for time allows us to look up previously seen elements instantly."
        if self.has_sort:
            return "Pre-processing the data via sorting reveals patterns and adjacency that simplifies the main logic."
        return "Analysis required"

    def _guess_edge_cases(self) -> str:
        cases = []
        if re.search(r'\b(vector|string|list|array)\b', self.code, re.IGNORECASE):
            cases.append("- Empty data structures (`n == 0`)")
        if self.has_binary_search:
            cases.append("- Integer overflow when calculating `mid` (prefer `left + (right - left) / 2`)")
        if self.has_hash_map:
            cases.append("- Hash collisions (rare but possible in worst-case)")
        if not cases:
            return "Analysis required"
        return "\n".join(cases)

    def _guess_lessons(self) -> str:
        if self.has_hash_map:
            return "Key takeaway: Hash maps drastically reduce time complexity by trading O(N) space for O(1) lookups."
        if self.has_sort:
            return "Key takeaway: Sorting is a powerful pre-processing step that often reduces search complexities."
        if self.has_two_pointers:
            return "Key takeaway: Two pointers optimally navigate bounded monotonic sequences without O(N^2) pairs."
        return "Analysis required"
