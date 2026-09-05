class Solution {
public:
    int removeDuplicates(vector<int>& nums) {

        int pt1 = 0;
        int pt2 = 1;
        int unique = 1;

        while (pt2 < nums.size()) {

            if (nums[pt2] == nums[pt2 - 1]) {
                pt2++;
                continue;
            }

            nums[pt1 + 1] = nums[pt2];
            pt1++;
            pt2++;
            unique++;
        }

        return unique;
    }
};
